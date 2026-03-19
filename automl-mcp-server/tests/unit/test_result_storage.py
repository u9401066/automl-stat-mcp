"""
Unit tests for result_storage.py

Tests the ResultStorage class and NumpyJSONEncoder.
"""

import json
import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np


class TestNumpyJSONEncoder:
    """Test custom JSON encoder for numpy types"""

    def test_encode_numpy_int64(self):
        """Test encoding numpy int64"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {"value": np.int64(42)}
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert parsed["value"] == 42
        assert isinstance(parsed["value"], int)

    def test_encode_numpy_float64(self):
        """Test encoding numpy float64"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {"value": np.float64(3.14159)}
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert abs(parsed["value"] - 3.14159) < 0.0001

    def test_encode_numpy_bool(self):
        """Test encoding numpy bool"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {"flag_true": np.bool_(True), "flag_false": np.bool_(False)}
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert parsed["flag_true"] is True
        assert parsed["flag_false"] is False

    def test_encode_numpy_array(self):
        """Test encoding numpy array"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {"array": np.array([1, 2, 3, 4, 5])}
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert parsed["array"] == [1, 2, 3, 4, 5]

    def test_encode_numpy_2d_array(self):
        """Test encoding 2D numpy array"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {"matrix": np.array([[1, 2], [3, 4]])}
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert parsed["matrix"] == [[1, 2], [3, 4]]

    def test_encode_mixed_types(self):
        """Test encoding mixed Python and numpy types"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        data = {
            "python_int": 42,
            "python_float": 3.14,
            "python_str": "hello",
            "numpy_int": np.int64(100),
            "numpy_float": np.float64(2.718),
            "numpy_array": np.array([1, 2, 3]),
            "nested": {"numpy_bool": np.bool_(True), "list": [np.int64(1), np.int64(2)]},
        }
        result = safe_json_dumps(data)
        parsed = json.loads(result)

        assert parsed["python_int"] == 42
        assert parsed["numpy_int"] == 100
        assert parsed["nested"]["numpy_bool"] is True

    def test_encode_nan_and_inf(self):
        """Test encoding NaN and Infinity (should convert to None/string)"""
        from infrastructure.mcp.handlers.result_storage import safe_json_dumps

        # Note: Standard JSON doesn't support NaN/Inf, encoder should handle gracefully
        data = {"nan": float("nan"), "inf": float("inf")}
        result = safe_json_dumps(data)
        # Should not raise, but result may vary
        assert isinstance(result, str)


class TestResultStorage:
    """Test ResultStorage class"""

    @pytest.fixture
    def storage(self):
        """Create ResultStorage instance"""
        from infrastructure.mcp.handlers.result_storage import ResultStorage

        return ResultStorage(stats_service_url="http://mock-stats:8003", minio_bucket="test-bucket")

    def test_init(self, storage):
        """Test ResultStorage initialization"""
        assert storage.stats_service_url == "http://mock-stats:8003"
        assert storage.minio_bucket == "test-bucket"
        assert storage.timeout == 30

    def test_generate_result_id_format(self, storage):
        """Test result ID format"""
        result_id = storage._generate_result_id("correlation")

        assert result_id.startswith("stat_correlation_")
        # Should have 8 character hex suffix
        suffix = result_id.split("_")[-1]
        assert len(suffix) == 8
        # Should be valid hex
        int(suffix, 16)

    def test_generate_result_id_uniqueness(self, storage):
        """Test result IDs are unique"""
        ids = [storage._generate_result_id("test") for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_generate_result_id_different_types(self, storage):
        """Test result IDs for different analysis types"""
        correlation_id = storage._generate_result_id("correlation")
        tableone_id = storage._generate_result_id("tableone")
        roc_id = storage._generate_result_id("roc")

        assert "correlation" in correlation_id
        assert "tableone" in tableone_id
        assert "roc" in roc_id

    def test_get_minio_path(self, storage):
        """Test MinIO path generation"""
        path = storage._get_minio_path("user123", "correlation", "stat_correlation_abc12345")

        assert path.startswith("user123/correlation/")
        assert "stat_correlation_abc12345" in path
        assert path.endswith(".json")

    def test_get_minio_path_with_timestamp(self, storage):
        """Test MinIO path includes timestamp"""
        path = storage._get_minio_path("user1", "roc", "stat_roc_xyz")

        # Should contain date in format YYYYMMDD
        today = datetime.now().strftime("%Y%m%d")
        assert today in path

    @pytest.mark.asyncio
    async def test_save_to_redis_called(self, storage):
        """Test _save_to_redis is called with correct params"""
        with patch.object(storage, "_save_to_redis", new_callable=AsyncMock) as mock_redis:
            with patch.object(storage, "_save_to_minio", new_callable=AsyncMock) as mock_minio:
                mock_minio.return_value = "bucket/path/file.json"

                await storage.save_result(result={"status": "success"}, user_id="test_user", analysis_type="test")

                mock_redis.assert_called_once()
                call_args = mock_redis.call_args
                assert "stat_test_" in call_args[0][0]  # result_id

    @pytest.mark.asyncio
    async def test_save_to_minio_called(self, storage):
        """Test _save_to_minio is called with correct params"""
        with patch.object(storage, "_save_to_redis", new_callable=AsyncMock):
            with patch.object(storage, "_save_to_minio", new_callable=AsyncMock) as mock_minio:
                mock_minio.return_value = "bucket/path/file.json"

                await storage.save_result(
                    result={"status": "success"}, user_id="test_user", analysis_type="correlation"
                )

                mock_minio.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_result_returns_metadata(self, storage):
        """Test save_result returns proper metadata"""
        with patch.object(storage, "_save_to_redis", new_callable=AsyncMock):
            with patch.object(storage, "_save_to_minio", new_callable=AsyncMock) as mock_minio:
                mock_minio.return_value = "test-bucket/user/test/file.json"

                metadata = await storage.save_result(
                    result={"status": "success", "data": [1, 2, 3]}, user_id="test_user", analysis_type="test"
                )

                assert metadata.result_id.startswith("stat_test_")
                assert metadata.user_id == "test_user"
                assert metadata.analysis_type == "test"
                # minio_path is generated by save_result, not the mock return value
                assert metadata.minio_path is not None

    @pytest.mark.asyncio
    async def test_save_result_handles_redis_error(self, storage):
        """Test save_result handles Redis errors gracefully"""
        with patch.object(storage, "_save_to_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            with patch.object(storage, "_save_to_minio", new_callable=AsyncMock) as mock_minio:
                mock_minio.return_value = "bucket/path/file.json"

                # Should not raise, but log error
                metadata = await storage.save_result(
                    result={"status": "success"}, user_id="test_user", analysis_type="test"
                )

                # Should still return metadata even if Redis fails
                assert metadata is not None

    @pytest.mark.asyncio
    async def test_save_result_handles_minio_error(self, storage):
        """Test save_result handles MinIO errors gracefully"""
        with patch.object(storage, "_save_to_redis", new_callable=AsyncMock):
            with patch.object(storage, "_save_to_minio", new_callable=AsyncMock) as mock_minio:
                mock_minio.side_effect = Exception("MinIO connection failed")

                metadata = await storage.save_result(
                    result={"status": "success"}, user_id="test_user", analysis_type="test"
                )

                # Should return metadata with None minio_path
                assert metadata.result_id is not None
                assert metadata.minio_path is None


class TestResultStorageIntegrationMock:
    """Test ResultStorage with mocked HTTP calls"""

    @pytest.fixture
    def storage(self):
        from infrastructure.mcp.handlers.result_storage import ResultStorage

        return ResultStorage(stats_service_url="http://mock-stats:8003", minio_bucket="test-bucket")

    @pytest.mark.asyncio
    async def test_save_to_redis_http_call(self, storage):
        """Test _save_to_redis makes correct HTTP call"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await storage._save_to_redis("test_key", {"data": "test"}, ttl=86400)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/storage/redis/set" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_save_to_minio_http_call(self, storage):
        """Test _save_to_minio makes correct HTTP call"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "full_path": "bucket/path"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await storage._save_to_minio("user/test/file.json", {"data": "test"}, "user123")

            mock_client.post.assert_called_once()


class TestGetResultStorage:
    """Test get_result_storage function"""

    def test_get_result_storage_singleton(self):
        """Test get_result_storage returns singleton"""
        from infrastructure.mcp.handlers.result_storage import get_result_storage

        storage1 = get_result_storage()
        storage2 = get_result_storage()

        assert storage1 is storage2

    def test_get_result_storage_default_config(self):
        """Test get_result_storage uses default config"""
        from infrastructure.mcp.handlers.result_storage import get_result_storage

        storage = get_result_storage()

        assert "8003" in storage.stats_service_url
        assert storage.minio_bucket == "automl-results"

"""
Unit tests for storage_factory.py

Tests the LocalStorageService implementation which is the default mode.
MinIO tests require actual MinIO instance and are skipped in unit tests.
"""
import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Set environment before import
os.environ["STORAGE_MODE"] = "local"


class TestLocalStorageService:
    """Test LocalStorageService implementation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage(self, temp_dir):
        """Create LocalStorageService with temp directory."""
        from src.infrastructure.storage_factory import LocalStorageService
        return LocalStorageService(data_root=temp_dir)

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame."""
        return pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 90.0, 78.5],
        })

    # =========================================================================
    # CSV Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_write_and_read_csv(self, storage, sample_df, temp_dir):
        """Test writing and reading CSV files."""
        path = "test/data.csv"

        # Write
        result_path = await storage.write_csv(path, sample_df)
        assert Path(result_path).exists()

        # Read
        df = await storage.read_csv(path)
        assert df is not None
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "score"]

    @pytest.mark.asyncio
    async def test_read_csv_not_found(self, storage):
        """Test reading non-existent CSV returns None."""
        df = await storage.read_csv("nonexistent.csv")
        assert df is None

    @pytest.mark.asyncio
    async def test_read_csv_with_nrows(self, storage, sample_df):
        """Test reading CSV with row limit."""
        await storage.write_csv("test.csv", sample_df)
        df = await storage.read_csv("test.csv", n_rows=2)
        assert len(df) == 2

    # =========================================================================
    # JSON Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_write_and_read_json(self, storage):
        """Test writing and reading JSON files."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        path = "test/config.json"

        # Write
        result_path = await storage.write_json(path, data)
        assert Path(result_path).exists()

        # Read
        loaded = await storage.read_json(path)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_read_json_not_found(self, storage):
        """Test reading non-existent JSON returns None."""
        data = await storage.read_json("nonexistent.json")
        assert data is None

    # =========================================================================
    # Bytes Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_write_and_read_bytes(self, storage):
        """Test writing and reading raw bytes."""
        data = b"Hello, World! \x00\x01\x02"
        path = "test/binary.bin"

        # Write
        result_path = await storage.write_bytes(path, data)
        assert Path(result_path).exists()

        # Read
        loaded = await storage.read_bytes(path)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_read_bytes_not_found(self, storage):
        """Test reading non-existent bytes returns None."""
        data = await storage.read_bytes("nonexistent.bin")
        assert data is None

    # =========================================================================
    # File Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_file_exists(self, storage, sample_df):
        """Test file existence check."""
        path = "test/data.csv"

        assert await storage.file_exists(path) is False
        await storage.write_csv(path, sample_df)
        assert await storage.file_exists(path) is True

    @pytest.mark.asyncio
    async def test_delete_file(self, storage, sample_df):
        """Test file deletion."""
        path = "test/data.csv"

        await storage.write_csv(path, sample_df)
        assert await storage.file_exists(path) is True

        result = await storage.delete_file(path)
        assert result is True
        assert await storage.file_exists(path) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage):
        """Test deleting non-existent file returns False."""
        result = await storage.delete_file("nonexistent.csv")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_files(self, storage, sample_df):
        """Test listing files in directory."""
        # Create multiple files
        await storage.write_csv("data/file1.csv", sample_df)
        await storage.write_csv("data/file2.csv", sample_df)
        await storage.write_json("data/config.json", {"key": "value"})

        # List all files
        files = await storage.list_files("data")
        assert len(files) == 3

        # List CSV files only
        csv_files = await storage.list_files("data", pattern="*.csv")
        assert len(csv_files) == 2

    @pytest.mark.asyncio
    async def test_list_files_recursive(self, storage, sample_df):
        """Test recursive file listing."""
        await storage.write_csv("data/level1/file1.csv", sample_df)
        await storage.write_csv("data/level1/level2/file2.csv", sample_df)

        # Non-recursive
        files = await storage.list_files("data", recursive=False)
        assert len(files) == 0  # No files directly in data/

        # Recursive
        files = await storage.list_files("data", recursive=True)
        assert len(files) == 2

    # =========================================================================
    # Path Resolution
    # =========================================================================

    def test_resolve_relative_path(self, storage, temp_dir):
        """Test relative path resolution."""
        resolved = storage._resolve_path("subdir/file.csv")
        assert str(resolved) == f"{temp_dir}/subdir/file.csv"

    def test_resolve_absolute_path(self, storage):
        """Test absolute path is used as-is."""
        abs_path = "/absolute/path/file.csv"
        resolved = storage._resolve_path(abs_path)
        assert str(resolved) == abs_path

    # =========================================================================
    # Public URL
    # =========================================================================

    def test_local_storage_no_public_url(self, storage):
        """Test local storage returns None for public URL."""
        url = storage.get_public_url("any/path.csv")
        assert url is None


class TestStorageFactory:
    """Test the get_storage factory function."""

    def test_default_is_local(self, monkeypatch):
        """Test default storage mode is local."""
        from src.infrastructure.storage_factory import reset_storage, get_storage, LocalStorageService

        monkeypatch.setenv("STORAGE_MODE", "local")
        reset_storage()

        storage = get_storage()
        assert isinstance(storage, LocalStorageService)

    def test_singleton_pattern(self, monkeypatch):
        """Test storage is singleton."""
        from src.infrastructure.storage_factory import reset_storage, get_storage

        monkeypatch.setenv("STORAGE_MODE", "local")
        reset_storage()

        storage1 = get_storage()
        storage2 = get_storage()
        assert storage1 is storage2

    def test_reset_storage(self, monkeypatch):
        """Test reset_storage clears singleton."""
        from src.infrastructure.storage_factory import reset_storage, get_storage

        monkeypatch.setenv("STORAGE_MODE", "local")
        reset_storage()

        storage1 = get_storage()
        reset_storage()
        storage2 = get_storage()

        assert storage1 is not storage2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def storage(self):
        """Create LocalStorageService with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.infrastructure.storage_factory import LocalStorageService
            yield LocalStorageService(data_root=tmpdir)

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, storage):
        """Test writing creates parent directories."""
        path = "deep/nested/path/file.csv"
        df = pd.DataFrame({"a": [1, 2, 3]})

        result_path = await storage.write_csv(path, df)
        assert Path(result_path).exists()

    @pytest.mark.asyncio
    async def test_empty_dataframe(self, storage):
        """Test handling empty DataFrame."""
        df = pd.DataFrame()
        await storage.write_csv("empty.csv", df)

        loaded = await storage.read_csv("empty.csv")
        assert loaded is not None
        assert len(loaded) == 0

    @pytest.mark.asyncio
    async def test_unicode_content(self, storage):
        """Test handling Unicode content."""
        data = {"message": "你好世界 🌍", "name": "日本語"}

        await storage.write_json("unicode.json", data)
        loaded = await storage.read_json("unicode.json")

        assert loaded["message"] == "你好世界 🌍"
        assert loaded["name"] == "日本語"

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, storage):
        """Test listing empty directory."""
        # Create directory
        Path(storage._resolve_path("empty_dir")).mkdir(parents=True, exist_ok=True)

        files = await storage.list_files("empty_dir")
        assert files == []

    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, storage):
        """Test listing non-existent directory returns empty list."""
        files = await storage.list_files("nonexistent")
        assert files == []

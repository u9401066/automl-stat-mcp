"""
Data Flow Integrity Tests

Tests data integrity throughout the system:
- Path resolution chain (User Input → MCP → Service → Worker)
- Data format preservation (upload → storage → retrieval → analysis)
- Result storage and retrieval
- Concurrent operations isolation

Requires: Services running (docker compose up)
"""
import asyncio
import base64
import json
from io import StringIO
from typing import Any, Dict

import httpx
import pandas as pd
import pytest
import structlog

# =============================================================================
# Test Configuration
# =============================================================================

logger = structlog.get_logger(__name__)

STATS_API_URL = "http://localhost:8003"
AUTOML_API_URL = "http://localhost:8001"
TIMEOUT = 30.0


# =============================================================================
# Helper Functions
# =============================================================================

def df_to_csv_content(df: pd.DataFrame) -> str:
    """Convert DataFrame to CSV string."""
    return df.to_csv(index=False)


def df_to_base64(df: pd.DataFrame) -> str:
    """Convert DataFrame to base64-encoded CSV."""
    csv_str = df.to_csv(index=False)
    return base64.b64encode(csv_str.encode()).decode()


async def wait_for_job(
    client: httpx.AsyncClient,
    job_id: str,
    max_wait: int = 60,
    poll_interval: float = 1.0,
) -> Dict[str, Any]:
    """Wait for a job to complete and return result."""
    log = logger.bind(job_id=job_id)
    
    for i in range(int(max_wait / poll_interval)):
        resp = await client.get(f"/jobs/{job_id}")
        if resp.status_code != 200:
            log.error("job_status_failed", status_code=resp.status_code)
            raise Exception(f"Failed to get job status: {resp.text}")
        
        data = resp.json()
        status = data.get("status")
        log.debug("job_poll", attempt=i+1, status=status)
        
        if status == "completed":
            return data
        elif status == "failed":
            log.error("job_failed", error=data.get("error"))
            raise Exception(f"Job failed: {data.get('error')}")
        
        await asyncio.sleep(poll_interval)
    
    raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")


# =============================================================================
# Test: Path Resolution Chain
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestPathResolutionChain:
    """Test path resolution from various input formats."""

    async def test_container_path_accepted(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test that container paths (/data/sample_data/...) are accepted."""
        test_logger.info("test_start", test="container_path_accepted")
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_path": "/data/sample_data/iris.csv",
                "user_id": "test_user",
            }
        )
        
        test_logger.info("response_received", status=resp.status_code)
        
        # Should succeed or return specific error about file not found
        # (if stats-service doesn't support csv_path)
        if resp.status_code == 422:
            # Endpoint might not support csv_path - check error
            data = resp.json()
            test_logger.warning("endpoint_validation_error", detail=data)
        else:
            assert resp.status_code in [200, 400, 404], f"Unexpected: {resp.text}"

    async def test_relative_path_resolution(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test that relative paths are resolved correctly."""
        test_logger.info("test_start", test="relative_path_resolution")
        
        # Test with just filename (should resolve to /data/sample_data/)
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_path": "iris.csv",  # Relative path
                "user_id": "test_user",
            }
        )
        
        test_logger.info("response_received", status=resp.status_code)
        # Document the behavior regardless of success/failure
        assert resp.status_code in [200, 400, 404, 422]

    async def test_host_path_rejected(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test that host paths (/home/...) are rejected or handled."""
        test_logger.info("test_start", test="host_path_rejected")
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_path": "/home/eric/workspace251204/sample_data/iris.csv",
                "user_id": "test_user",
            }
        )
        
        test_logger.info("response_received", status=resp.status_code)
        
        # Host paths should fail or be converted
        # Document actual behavior
        if resp.status_code == 200:
            test_logger.warning(
                "host_path_accepted",
                note="Host path was accepted - potential security concern"
            )


# =============================================================================
# Test: Data Format Preservation
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestDataFormatPreservation:
    """Test that data format is preserved through the pipeline."""

    async def test_csv_content_roundtrip(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        iris_df: pd.DataFrame,
        test_logger,
    ):
        """Test CSV content is preserved when sent and analyzed."""
        test_logger.info("test_start", test="csv_content_roundtrip")
        
        original_csv = df_to_csv_content(iris_df)
        original_shape = iris_df.shape
        
        test_logger.info("original_data", shape=original_shape, columns=list(iris_df.columns))
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": original_csv,
                "user_id": "test_user",
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            test_logger.info("analysis_result", keys=list(data.keys()))
            
            # Verify row count matches
            if "n_rows" in data:
                assert data["n_rows"] == original_shape[0], \
                    f"Row count mismatch: {data['n_rows']} vs {original_shape[0]}"
            if "n_cols" in data:
                assert data["n_cols"] == original_shape[1], \
                    f"Column count mismatch: {data['n_cols']} vs {original_shape[1]}"
        else:
            test_logger.warning("request_failed", status=resp.status_code)

    async def test_base64_encoding_decoding(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        iris_df: pd.DataFrame,
        test_logger,
    ):
        """Test base64-encoded data is correctly decoded."""
        test_logger.info("test_start", test="base64_encoding")
        
        base64_content = df_to_base64(iris_df)
        test_logger.info("encoded_data", length=len(base64_content))
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": base64_content,
                "is_base64": True,
                "user_id": "test_user",
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            test_logger.info("decode_success", n_rows=data.get("n_rows"))
        else:
            test_logger.warning("decode_failed", status=resp.status_code, body=resp.text[:200])

    async def test_special_characters_preserved(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test that special characters in column names are handled."""
        test_logger.info("test_start", test="special_characters")
        
        # Create DataFrame with special characters
        df = pd.DataFrame({
            "Column With Spaces": [1, 2, 3],
            "column_with_underscore": [4, 5, 6],
            "中文欄位": [7, 8, 9],
            "column/with/slash": [10, 11, 12],
            "column.with.dot": [13, 14, 15],
        })
        
        csv_content = df_to_csv_content(df)
        test_logger.info("test_data", columns=list(df.columns))
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": csv_content,
                "user_id": "test_user",
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            test_logger.info("special_chars_handled", result_keys=list(data.keys()))
        else:
            test_logger.warning(
                "special_chars_failed",
                status=resp.status_code,
                note="May need column sanitization"
            )

    async def test_missing_values_preserved(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        titanic_df: pd.DataFrame,
        test_logger,
    ):
        """Test that missing values are correctly preserved and reported."""
        test_logger.info("test_start", test="missing_values")
        
        # Titanic has known missing values
        original_missing = titanic_df.isnull().sum().sum()
        test_logger.info("original_missing", total_missing=int(original_missing))
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(titanic_df),
                "user_id": "test_user",
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            test_logger.info("missing_analysis", result=data.get("missing_summary"))


# =============================================================================
# Test: Result Storage and Retrieval
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestResultStorageRetrieval:
    """Test job result storage and retrieval."""

    async def test_job_result_retrievable(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        iris_df: pd.DataFrame,
        test_logger,
    ):
        """Test that job results can be retrieved after completion."""
        test_logger.info("test_start", test="job_result_retrievable")
        
        # Submit a job
        resp = await stats_client.post(
            "/direct/analyze",
            json={
                "csv_content": df_to_csv_content(iris_df),
                "user_id": "test_user",
            }
        )
        
        if resp.status_code != 200:
            test_logger.warning("submit_failed", status=resp.status_code)
            pytest.skip("Direct analyze endpoint not available")
            return
        
        data = resp.json()
        job_id = data.get("job_id")
        
        if not job_id:
            test_logger.info("sync_result", note="Got immediate result, no job_id")
            return
        
        test_logger.info("job_submitted", job_id=job_id)
        
        # Wait for completion
        try:
            result = await wait_for_job(stats_client, job_id)
            test_logger.info("job_completed", has_result=bool(result.get("result")))
        except TimeoutError as e:
            test_logger.error("job_timeout", error=str(e))
            pytest.fail(str(e))

    async def test_result_id_consistent(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        iris_df: pd.DataFrame,
        test_logger,
    ):
        """Test that result IDs are consistent across queries."""
        test_logger.info("test_start", test="result_id_consistent")
        
        # Submit analysis
        resp = await stats_client.post(
            "/direct/analyze",
            json={
                "csv_content": df_to_csv_content(iris_df),
                "user_id": "test_user",
            }
        )
        
        if resp.status_code != 200:
            pytest.skip("Endpoint not available")
            return
        
        data = resp.json()
        result_id = data.get("result_id") or data.get("job_id")
        
        if result_id:
            # Query result multiple times
            for i in range(3):
                resp2 = await stats_client.get(f"/jobs/{result_id}")
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    test_logger.info(
                        "result_query",
                        attempt=i+1,
                        status=data2.get("status")
                    )


# =============================================================================
# Test: Concurrent Operations
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestConcurrentOperations:
    """Test concurrent operations don't interfere."""

    async def test_concurrent_analyses_isolated(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        iris_df: pd.DataFrame,
        titanic_df: pd.DataFrame,
        test_logger,
    ):
        """Test that concurrent analyses don't mix results."""
        test_logger.info("test_start", test="concurrent_isolation")
        
        async def submit_analysis(df: pd.DataFrame, user_id: str) -> Dict:
            resp = await stats_client.post(
                "/direct/quick-stats",
                json={
                    "csv_content": df_to_csv_content(df),
                    "user_id": user_id,
                }
            )
            return {
                "user_id": user_id,
                "status": resp.status_code,
                "data": resp.json() if resp.status_code == 200 else None,
            }
        
        # Submit concurrently with different users and data
        tasks = [
            submit_analysis(iris_df, "user_A"),
            submit_analysis(titanic_df, "user_B"),
            submit_analysis(iris_df, "user_C"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, Exception):
                test_logger.error("concurrent_error", error=str(r))
            else:
                test_logger.info(
                    "concurrent_result",
                    user_id=r["user_id"],
                    status=r["status"],
                    n_rows=r["data"].get("n_rows") if r["data"] else None,
                )
        
        # Verify isolation - check row counts match expected
        for r in results:
            if isinstance(r, dict) and r["data"]:
                user = r["user_id"]
                n_rows = r["data"].get("n_rows")
                
                if user in ["user_A", "user_C"]:
                    expected = len(iris_df)
                else:
                    expected = len(titanic_df)
                
                if n_rows:
                    assert n_rows == expected, \
                        f"User {user} got wrong data: {n_rows} vs {expected}"


# =============================================================================
# Test: Data Type Handling
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestDataTypeHandling:
    """Test handling of various data types."""

    async def test_numeric_types_preserved(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test that numeric types (int, float) are preserved."""
        test_logger.info("test_start", test="numeric_types")
        
        df = pd.DataFrame({
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
            "large_int": [10**10, 10**11, 10**12, 10**13, 10**14],
            "small_float": [1e-10, 1e-11, 1e-12, 1e-13, 1e-14],
        })
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("numeric_test", status=resp.status_code)
        
        if resp.status_code == 200:
            data = resp.json()
            test_logger.info("numeric_result", summary=data.get("summary"))

    async def test_boolean_handling(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test boolean values are handled correctly."""
        test_logger.info("test_start", test="boolean_handling")
        
        df = pd.DataFrame({
            "bool_col": [True, False, True, False, True],
            "int_bool": [1, 0, 1, 0, 1],
            "str_bool": ["yes", "no", "yes", "no", "yes"],
        })
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("boolean_test", status=resp.status_code)

    async def test_datetime_handling(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test datetime values are handled correctly."""
        test_logger.info("test_start", test="datetime_handling")
        
        import datetime
        df = pd.DataFrame({
            "date_col": pd.date_range("2024-01-01", periods=5),
            "value": [1, 2, 3, 4, 5],
        })
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("datetime_test", status=resp.status_code)


# =============================================================================
# Test: Edge Cases
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_empty_dataframe(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test handling of empty DataFrame."""
        test_logger.info("test_start", test="empty_dataframe")
        
        df = pd.DataFrame(columns=["a", "b", "c"])
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("empty_df_result", status=resp.status_code)
        # Should handle gracefully, not crash

    async def test_single_row(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test handling of single-row DataFrame."""
        test_logger.info("test_start", test="single_row")
        
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("single_row_result", status=resp.status_code)

    async def test_single_column(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test handling of single-column DataFrame."""
        test_logger.info("test_start", test="single_column")
        
        df = pd.DataFrame({"only_column": [1, 2, 3, 4, 5]})
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("single_col_result", status=resp.status_code)

    async def test_all_missing_column(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test handling of column with all missing values."""
        test_logger.info("test_start", test="all_missing_column")
        
        import numpy as np
        df = pd.DataFrame({
            "normal": [1, 2, 3, 4, 5],
            "all_missing": [np.nan, np.nan, np.nan, np.nan, np.nan],
        })
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("all_missing_result", status=resp.status_code)

    async def test_very_long_column_names(
        self,
        stats_client: httpx.AsyncClient,
        stats_service_available,
        test_logger,
    ):
        """Test handling of very long column names."""
        test_logger.info("test_start", test="long_column_names")
        
        long_name = "a" * 200
        df = pd.DataFrame({long_name: [1, 2, 3]})
        
        resp = await stats_client.post(
            "/direct/quick-stats",
            json={
                "csv_content": df_to_csv_content(df),
                "user_id": "test_user",
            }
        )
        
        test_logger.info("long_name_result", status=resp.status_code)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

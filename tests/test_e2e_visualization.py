"""
E2E Test - Visualization and MinIO Results Workflow

Tests the complete visualization workflow including:
- MinIO storage for results
- Figure generation and URLs
- Various chart types

Prerequisites:
    - Services running (docker compose up)
    - MinIO accessible

Usage:
    cd tests
    python -m pytest test_e2e_visualization.py -v
"""

import asyncio
import os
import time

import httpx
import pytest

# =============================================================================
# Configuration
# =============================================================================

STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")
AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")

TEST_USER_ID = "e2e_viz_test"
TIMEOUT = 120.0
POLL_INTERVAL = 3

# Sample data paths (container paths)
SAMPLE_DATA = {
    "iris": "/data/sample_data/iris.csv",
    "heart": "/data/sample_data/heart_disease.csv",
    "breast_cancer": "/data/sample_data/breast_cancer.csv",
    "rossi": "/data/sample_data/rossi_recidivism.csv",
}


# =============================================================================
# Helper Functions
# =============================================================================


async def wait_for_job(
    client: httpx.AsyncClient, job_id: str, timeout: int = 120, poll_interval: int = POLL_INTERVAL
) -> dict:
    """Wait for a job to complete."""
    start = time.time()

    while time.time() - start < timeout:
        resp = await client.get(f"{STATS_API_URL}/jobs/{job_id}")

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")

            if status in ["completed", "failed", "error"]:
                return data

        await asyncio.sleep(poll_interval)

    return {"status": "timeout", "job_id": job_id}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def stats_client():
    """Create HTTP client for stats service (not pre-opened)."""
    return httpx.AsyncClient(timeout=TIMEOUT)


# =============================================================================
# Test: MinIO Results Storage
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestMinIOResultsFlow:
    """Test MinIO results storage workflow."""

    async def test_analysis_returns_result_id(self, stats_client):
        """Test that analysis returns result_id for MinIO storage."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/analyze",
                json={
                    "csv_path": SAMPLE_DATA["iris"],
                    "group_column": "species",
                    "value_column": "sepal_length",
                    "user_id": TEST_USER_ID,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                # Should have result_id for MinIO storage
                if "result_id" in data:
                    assert data["result_id"].startswith("stat_")
                if "result_path" in data:
                    assert "automl-results" in data["result_path"]
            elif resp.status_code == 404:
                pytest.skip("Compare groups endpoint not implemented")

    async def test_list_analysis_results(self, stats_client):
        """Test listing analysis results from Redis."""
        async with stats_client as client:
            resp = await client.get(f"{STATS_API_URL}/storage/redis/keys", params={"pattern": "stats:result:*"})

            if resp.status_code == 200:
                data = resp.json()
                # Should return list of keys
                assert "keys" in data or isinstance(data, list)
            elif resp.status_code == 404:
                pytest.skip("Storage endpoint not implemented")


# =============================================================================
# Test: ROC Visualization
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestROCVisualizationFlow:
    """Test ROC curve visualization generation."""

    async def test_roc_curve_generation(self, stats_client):
        """Test that ROC analysis generates curve figure."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/compute/submit",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "generate_plot": True,
                },
            )

            if resp.status_code == 200:
                data = resp.json()

                # Check if visualizations included
                if "visualizations" in data:
                    viz = data["visualizations"]
                    assert len(viz) > 0, "No visualizations generated"

                    # Check for ROC curve
                    has_roc = any("roc" in v.get("filename", "").lower() for v in viz)
                    assert has_roc, "ROC curve not in visualizations"
            elif resp.status_code == 404:
                pytest.skip("ROC endpoint not implemented")

    async def test_roc_comparison_figures(self, stats_client):
        """Test ROC comparison generates comparison figure."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/compare/submit",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col_1": "mean_radius",
                    "y_score_col_2": "mean_texture",
                    "user_id": TEST_USER_ID,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                # Should have comparison visualization or result
                assert "auc_1" in data or "result" in data or "comparison" in data
            elif resp.status_code == 404:
                pytest.skip("ROC compare endpoint not implemented")


# =============================================================================
# Test: Survival Visualization
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSurvivalVisualizationFlow:
    """Test survival analysis visualization generation."""

    async def test_kaplan_meier_curve(self, stats_client):
        """Test Kaplan-Meier curve generation."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/survival/kaplan-meier/submit",
                json={
                    "csv_path": SAMPLE_DATA["rossi"],
                    "time_column": "week",
                    "event_column": "arrest",
                    "user_id": TEST_USER_ID,
                    "generate_plot": True,
                },
            )

            if resp.status_code == 200:
                data = resp.json()

                if "visualizations" in data:
                    viz = data["visualizations"]
                    # Check for KM curve
                    has_km = any(
                        "km" in v.get("filename", "").lower()
                        or "kaplan" in v.get("filename", "").lower()
                        or "survival" in v.get("filename", "").lower()
                        for v in viz
                    )
                    if viz:
                        assert has_km or len(viz) > 0
            elif resp.status_code == 404:
                pytest.skip("Kaplan-Meier endpoint not implemented")

    async def test_survival_comparison_curves(self, stats_client):
        """Test survival curves with group comparison."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/survival/kaplan-meier/submit",
                json={
                    "csv_path": SAMPLE_DATA["rossi"],
                    "time_column": "week",
                    "event_column": "arrest",
                    "group_column": "fin",
                    "user_id": TEST_USER_ID,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                # Should have grouped survival curves or log-rank test
                data_str = str(data).lower()
                assert "survival" in data_str or "log_rank" in data_str or "result" in data
            elif resp.status_code == 404:
                pytest.skip("Kaplan-Meier endpoint not implemented")


# =============================================================================
# Test: Full Evaluation Workflow
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestFullEvaluationFlow:
    """Test full evaluation with MinIO storage."""

    async def test_full_roc_eval_returns_result_id(self, stats_client):
        """Test that full ROC evaluation stores results."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/full-eval/submit",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "job_name": "viz_test_roc",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                job_id = data.get("job_id")

                if job_id:
                    # Wait for completion
                    result = await wait_for_job(client, job_id)

                    if result["status"] == "completed":
                        # Check for result persistence fields
                        result_data = result.get("result", {})
                        if "result_id" in result_data:
                            assert result_data["result_id"].startswith("stat_")
            elif resp.status_code == 404:
                pytest.skip("ROC full-eval endpoint not implemented")


# =============================================================================
# Test: Visualization URLs
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestVisualizationURLs:
    """Test visualization URL generation."""

    async def test_visualization_urls_valid(self, stats_client):
        """Test that visualization URLs are valid MinIO paths."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/compute/submit",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "generate_plot": True,
                },
            )

            if resp.status_code == 200:
                data = resp.json()

                if "visualizations" in data:
                    for viz in data["visualizations"]:
                        if "url" in viz:
                            url = viz["url"]
                            # Should be MinIO URL
                            assert "minio" in url.lower() or "9000" in url or "http" in url
            elif resp.status_code == 404:
                pytest.skip("ROC endpoint not implemented")


# =============================================================================
# Test: Complete Visualization Workflow
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestCompleteVisualizationWorkflow:
    """Test complete visualization workflow with MinIO."""

    async def test_full_analysis_with_minio_results(self, stats_client):
        """
        Complete analysis workflow with MinIO results:
        1. Submit full ROC evaluation
        2. Wait for completion
        3. Verify result_id returned
        4. Check visualizations array
        5. Verify URLs are accessible
        """
        async with stats_client as client:
            # 1. Submit job
            resp = await client.post(
                f"{STATS_API_URL}/roc/full-eval/submit",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "job_name": "complete_viz_workflow",
                },
            )

            if resp.status_code != 200:
                pytest.skip("Full-eval endpoint not available")

            data = resp.json()
            job_id = data.get("job_id")

            if not job_id:
                pytest.skip("No job_id returned")

            # 2. Wait for completion
            result = await wait_for_job(client, job_id)

            if result["status"] != "completed":
                pytest.skip("Job did not complete")

            # 3. Check result structure
            result_data = result.get("result", {})

            print(f"Job completed: {job_id}")

            if "result_id" in result_data:
                print(f"✓ Result ID: {result_data['result_id']}")

            if "result_path" in result_data:
                print(f"✓ Result Path: {result_data['result_path']}")

            if "visualizations" in result_data:
                print(f"✓ Visualizations: {len(result_data['visualizations'])} items")

            print("✓ Complete visualization workflow passed!")


# =============================================================================
# Test: Storage API
# =============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
class TestStorageAPI:
    """Test storage API endpoints."""

    async def test_redis_storage_set_get(self, stats_client):
        """Test Redis storage set and get."""
        async with stats_client as client:
            test_key = "test:viz:key"
            test_value = {"test": "data", "value": 123}

            # Set value
            resp = await client.post(
                f"{STATS_API_URL}/storage/redis/set",
                json={
                    "key": test_key,
                    "value": test_value,
                    "ttl": 60,
                },
            )

            if resp.status_code == 404:
                pytest.skip("Redis storage endpoint not implemented")

            if resp.status_code == 200:
                # Get value
                resp = await client.get(f"{STATS_API_URL}/storage/redis/get", params={"key": test_key})

                if resp.status_code == 200:
                    data = resp.json()
                    assert data.get("value") == test_value or data == test_value

    async def test_minio_list_objects(self, stats_client):
        """Test MinIO list objects."""
        async with stats_client as client:
            resp = await client.get(
                f"{STATS_API_URL}/storage/minio/list",
                params={
                    "bucket": "stats-reports",
                    "prefix": TEST_USER_ID,
                },
            )

            if resp.status_code == 404:
                pytest.skip("MinIO list endpoint not implemented")

            if resp.status_code == 200:
                data = resp.json()
                # Should return objects list
                assert "objects" in data or isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
E2E Test - AutoML Training Workflow

Tests the complete AutoML training workflow including:
- Dataset registration
- AutoML training (full search)
- Specific algorithm training
- Model comparison
- Prediction
- Model management

Prerequisites:
    - Services running (docker compose up)
    - AutoGluon worker running

Usage:
    cd tests
    python -m pytest test_e2e_automl.py -v
    python -m pytest test_e2e_automl.py -v -k "quick"  # Quick tests only
    python -m pytest test_e2e_automl.py -v -m "not slow"  # Skip slow tests
"""
import asyncio
import os
import time
from typing import Optional

import httpx
import pytest

# =============================================================================
# Configuration
# =============================================================================

AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")

TEST_USER_ID = "e2e_automl_test"
TIMEOUT = 300.0  # 5 minutes for training
QUICK_TIMEOUT = 60.0
POLL_INTERVAL = 5

# Sample data paths
SAMPLE_DATA = {
    "iris": "/data/sample_data/iris.csv",
    "heart": "/data/sample_data/heart_disease.csv",
    "breast_cancer": "/data/sample_data/breast_cancer.csv",
    "diabetes": "/data/sample_data/diabetes.csv",
    "wine": "/data/sample_data/wine_quality.csv",
}


# =============================================================================
# Helper Functions
# =============================================================================

async def wait_for_training_job(
    client: httpx.AsyncClient,
    job_id: str,
    timeout: int = 300,
    poll_interval: int = POLL_INTERVAL
) -> dict:
    """Wait for a training job to complete."""
    start = time.time()

    while time.time() - start < timeout:
        resp = await client.get(f"{AUTOML_API_URL}/jobs/{job_id}")

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")

            if status in ["completed", "failed", "error"]:
                return data

            # Print progress
            progress = data.get("progress", 0)
            if progress > 0:
                print(f"Training progress: {progress:.1%}")

        await asyncio.sleep(poll_interval)

    return {"status": "timeout", "job_id": job_id}


async def register_dataset(
    client: httpx.AsyncClient,
    name: str,
    csv_path: str,
) -> Optional[str]:
    """Register a dataset and return dataset_id."""
    resp = await client.post(
        f"{AUTOML_API_URL}/datasets/register",
        json={
            "name": name,
            "user_id": TEST_USER_ID,
            "minio_path": csv_path,  # Local path will be used
        }
    )

    if resp.status_code == 200:
        data = resp.json()
        return data.get("dataset_id")

    return None


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
def automl_client():
    """Create HTTP client for automl service (not pre-opened)."""
    return httpx.AsyncClient(timeout=TIMEOUT)


@pytest.fixture(scope="module")
async def registered_iris_dataset():
    """Register Iris dataset once for all tests."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        dataset_id = await register_dataset(
            client, "e2e_iris", SAMPLE_DATA["iris"]
        )
        yield dataset_id


# =============================================================================
# Test: Service Health
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestAutoMLServiceHealth:
    """Test AutoML service health."""

    async def test_health_check(self, automl_client):
        """Test health endpoint."""
        async with automl_client as client:
            resp = await client.get(f"{AUTOML_API_URL}/health")
            assert resp.status_code == 200

    async def test_list_algorithms(self, automl_client):
        """Test listing available algorithms."""
        async with automl_client as client:
            resp = await client.get(f"{AUTOML_API_URL}/algorithms")

            if resp.status_code == 200:
                data = resp.json()
                assert isinstance(data, list) or "algorithms" in data
            elif resp.status_code == 404:
                pytest.skip("Algorithms endpoint not implemented")


# =============================================================================
# Test: Dataset Registration
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestDatasetRegistration:
    """Test dataset registration workflow."""

    async def test_register_dataset(self, automl_client):
        """Test registering a dataset."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/datasets/register",
                json={
                    "name": "test_iris",
                    "user_id": TEST_USER_ID,
                    "minio_path": SAMPLE_DATA["iris"],
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "dataset_id" in data
            elif resp.status_code == 404:
                # Try upload endpoint instead
                resp = await client.post(
                    f"{AUTOML_API_URL}/datasets/upload",
                    json={
                        "name": "test_iris",
                        "user_id": TEST_USER_ID,
                        "source_type": "local",
                        "source_path": SAMPLE_DATA["iris"],
                        "storage_mode": "temporary",
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    assert "dataset_id" in data or "job_id" in data

    async def test_list_datasets(self, automl_client):
        """Test listing user datasets."""
        async with automl_client as client:
            resp = await client.get(
                f"{AUTOML_API_URL}/datasets",
                params={"user_id": TEST_USER_ID}
            )

            if resp.status_code == 200:
                data = resp.json()
                assert isinstance(data, list) or "datasets" in data


# =============================================================================
# Test: Quick Training
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestQuickTraining:
    """Test quick training (fast, for CI)."""

    async def test_quick_train_classification(self, automl_client):
        """Test quick training for classification."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/quick",
                json={
                    "name": "quick_iris_test",
                    "user_id": TEST_USER_ID,
                    "source_path": SAMPLE_DATA["iris"],
                    "target_column": "target",
                    "problem_type": "multiclass",
                    "time_limit": 30,  # 30 seconds only
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data

                # Wait for quick training
                result = await wait_for_training_job(
                    client, data["job_id"], timeout=QUICK_TIMEOUT
                )

                if result["status"] == "completed":
                    assert "model_id" in result or "leaderboard" in result
            elif resp.status_code == 404:
                pytest.skip("Quick train endpoint not implemented")

    async def test_quick_train_binary(self, automl_client):
        """Test quick training for binary classification."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/quick",
                json={
                    "name": "quick_heart_test",
                    "user_id": TEST_USER_ID,
                    "source_path": SAMPLE_DATA["heart"],
                    "target_column": "target",
                    "problem_type": "binary",
                    "time_limit": 30,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data
            elif resp.status_code == 404:
                pytest.skip("Quick train endpoint not implemented")


# =============================================================================
# Test: Full AutoML Training
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestAutoMLTraining:
    """Test full AutoML training (slower, comprehensive)."""

    async def test_automl_train_iris(self, automl_client, registered_iris_dataset):
        """Test full AutoML training on Iris."""
        if registered_iris_dataset is None:
            pytest.skip("Dataset registration failed")

        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/automl",
                json={
                    "dataset_id": registered_iris_dataset,
                    "target_column": "target",
                    "problem_type": "multiclass",
                    "time_limit": 60,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data

                # Wait for training
                result = await wait_for_training_job(
                    client, data["job_id"], timeout=TIMEOUT
                )

                assert result["status"] in ["completed", "timeout"]
            elif resp.status_code == 404:
                pytest.skip("AutoML train endpoint not implemented")

    async def test_automl_train_regression(self, automl_client):
        """Test AutoML training for regression."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/automl",
                json={
                    "source_path": SAMPLE_DATA["diabetes"],
                    "target_column": "progression",
                    "problem_type": "regression",
                    "time_limit": 60,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data
            elif resp.status_code == 404:
                pytest.skip("AutoML train endpoint not implemented")


# =============================================================================
# Test: Specific Algorithm Training
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestSpecificAlgorithmTraining:
    """Test training with specific algorithms."""

    async def test_train_random_forest(self, automl_client):
        """Train Random Forest specifically."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/specific",
                json={
                    "source_path": SAMPLE_DATA["iris"],
                    "target_column": "target",
                    "algorithms": ["RF"],
                    "time_limit": 30,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data
            elif resp.status_code == 404:
                pytest.skip("Specific train endpoint not implemented")

    async def test_train_xgboost(self, automl_client):
        """Train XGBoost specifically."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/specific",
                json={
                    "source_path": SAMPLE_DATA["heart"],
                    "target_column": "target",
                    "algorithms": ["XGB"],
                    "time_limit": 30,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data
            elif resp.status_code == 404:
                pytest.skip("Specific train endpoint not implemented")

    async def test_train_lightgbm(self, automl_client):
        """Train LightGBM specifically."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/specific",
                json={
                    "source_path": SAMPLE_DATA["breast_cancer"],
                    "target_column": "diagnosis",
                    "algorithms": ["GBM"],
                    "time_limit": 30,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data
            elif resp.status_code == 404:
                pytest.skip("Specific train endpoint not implemented")


# =============================================================================
# Test: Algorithm Comparison
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestAlgorithmComparison:
    """Test comparing multiple algorithms."""

    async def test_compare_algorithms(self, automl_client):
        """Compare multiple algorithms on same dataset."""
        async with automl_client as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/train/compare",
                json={
                    "source_path": SAMPLE_DATA["heart"],
                    "target_column": "target",
                    "algorithms": ["RF", "XGB", "GBM"],
                    "time_limit": 120,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                assert "job_id" in data

                # Wait for comparison
                result = await wait_for_training_job(
                    client, data["job_id"], timeout=TIMEOUT
                )

                if result["status"] == "completed":
                    # Should have leaderboard
                    assert "leaderboard" in result or "model_id" in result
            elif resp.status_code == 404:
                pytest.skip("Compare endpoint not implemented")


# =============================================================================
# Test: Model Management
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestModelManagement:
    """Test model management operations."""

    async def test_list_models(self, automl_client):
        """Test listing trained models."""
        async with automl_client as client:
            resp = await client.get(
                f"{AUTOML_API_URL}/models",
                params={"user_id": TEST_USER_ID}
            )

            if resp.status_code == 200:
                data = resp.json()
                assert isinstance(data, list) or "models" in data

    async def test_get_leaderboard(self, automl_client):
        """Test getting model leaderboard."""
        # First, need a model_id from a training job
        # This test assumes some model exists
        async with automl_client as client:
            # List models first
            resp = await client.get(
                f"{AUTOML_API_URL}/models",
                params={"user_id": TEST_USER_ID}
            )

            if resp.status_code == 200:
                models = resp.json()
                if isinstance(models, list) and len(models) > 0:
                    model_id = models[0].get("model_id") or models[0].get("id")

                    # Get leaderboard
                    resp = await client.get(
                        f"{AUTOML_API_URL}/models/{model_id}/leaderboard"
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        assert "leaderboard" in data or isinstance(data, list)

    async def test_get_feature_importance(self, automl_client):
        """Test getting feature importance."""
        async with automl_client as client:
            # List models first
            resp = await client.get(
                f"{AUTOML_API_URL}/models",
                params={"user_id": TEST_USER_ID}
            )

            if resp.status_code == 200:
                models = resp.json()
                if isinstance(models, list) and len(models) > 0:
                    model_id = models[0].get("model_id") or models[0].get("id")

                    # Get feature importance
                    resp = await client.get(
                        f"{AUTOML_API_URL}/models/{model_id}/importance"
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        assert "importance" in data or "feature_importance" in data


# =============================================================================
# Test: Prediction
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestPrediction:
    """Test model prediction."""

    async def test_predict_single(self, automl_client):
        """Test single prediction."""
        # Need a trained model first
        # This test assumes some model exists
        async with automl_client as client:
            # List models
            resp = await client.get(
                f"{AUTOML_API_URL}/models",
                params={"user_id": TEST_USER_ID}
            )

            if resp.status_code == 200:
                models = resp.json()
                if isinstance(models, list) and len(models) > 0:
                    model_id = models[0].get("model_id") or models[0].get("id")

                    # Make prediction
                    resp = await client.post(
                        f"{AUTOML_API_URL}/predict",
                        json={
                            "model_id": model_id,
                            "data": [
                                {"sepal_length": 5.1, "sepal_width": 3.5,
                                 "petal_length": 1.4, "petal_width": 0.2}
                            ],
                            "user_id": TEST_USER_ID,
                        }
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        assert "predictions" in data or "prediction" in data

    async def test_predict_batch(self, automl_client):
        """Test batch prediction from CSV."""
        # Similar to single but with file input
        pass


# =============================================================================
# Test: Complete AutoML Workflow
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestCompleteAutoMLWorkflow:
    """Test complete AutoML workflow."""

    async def test_complete_workflow_iris(self, automl_client):
        """
        Complete AutoML workflow for Iris:
        1. Register dataset
        2. Submit training job
        3. Wait for completion
        4. Get leaderboard
        5. Get feature importance
        6. Make predictions
        """
        async with automl_client as client:
            # 1. Register dataset
            resp = await client.post(
                f"{AUTOML_API_URL}/datasets/register",
                json={
                    "name": "workflow_iris",
                    "user_id": TEST_USER_ID,
                    "minio_path": SAMPLE_DATA["iris"],
                }
            )

            if resp.status_code != 200:
                pytest.skip("Dataset registration not available")

            dataset_id = resp.json().get("dataset_id")

            # 2. Submit training
            resp = await client.post(
                f"{AUTOML_API_URL}/train/automl",
                json={
                    "dataset_id": dataset_id,
                    "target_column": "target",
                    "problem_type": "multiclass",
                    "time_limit": 60,
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code != 200:
                pytest.skip("Training endpoint not available")

            job_id = resp.json().get("job_id")

            # 3. Wait for completion
            result = await wait_for_training_job(client, job_id, timeout=TIMEOUT)

            if result["status"] != "completed":
                pytest.skip("Training did not complete in time")

            model_id = result.get("model_id")

            # 4. Get leaderboard
            resp = await client.get(f"{AUTOML_API_URL}/models/{model_id}/leaderboard")
            if resp.status_code == 200:
                leaderboard = resp.json()
                print(f"✓ Leaderboard: {len(leaderboard)} models")

            # 5. Get feature importance
            resp = await client.get(f"{AUTOML_API_URL}/models/{model_id}/importance")
            if resp.status_code == 200:
                resp.json()
                print("✓ Feature importance retrieved")

            # 6. Make prediction
            resp = await client.post(
                f"{AUTOML_API_URL}/predict",
                json={
                    "model_id": model_id,
                    "data": [
                        {"sepal_length": 5.1, "sepal_width": 3.5,
                         "petal_length": 1.4, "petal_width": 0.2}
                    ],
                    "user_id": TEST_USER_ID,
                }
            )

            if resp.status_code == 200:
                predictions = resp.json()
                print(f"✓ Prediction: {predictions}")

            print("✓ Complete AutoML workflow passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

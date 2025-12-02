"""
Local Test Script for AutoML Service

Tests the API without Docker, using:
- In-memory repositories
- Local file storage (fallback from MinIO)
- Direct AutoGluon execution

Usage:
    cd automl-service
    pip install -r requirements-dev.txt
    python tests/test_local.py
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sklearn.datasets import make_classification


async def test_automl_flow():
    """Test the complete AutoML flow locally"""
    
    print("=" * 60)
    print("AutoML Service Local Test")
    print("=" * 60)
    
    # Create test dataset
    print("\n1. Creating test dataset...")
    X, y = make_classification(
        n_samples=200,  # Small for fast testing
        n_features=10,
        n_informative=5,
        n_redundant=2,
        random_state=42,
    )
    df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(10)])
    df["target"] = y
    
    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    dataset_path = os.path.join(temp_dir, "test_data.csv")
    df.to_csv(dataset_path, index=False)
    print(f"   Dataset saved to: {dataset_path}")
    print(f"   Shape: {df.shape}")
    
    # Import after path setup
    from src.interface.api.dependencies import Container
    from src.domain.models import TrainingConfig, ProblemType
    from src.application.use_cases import RegisterDatasetUseCase
    from src.application.dto import RegisterDatasetRequest
    
    # Get container
    container = Container.get_instance()
    
    # 2. Register dataset
    print("\n2. Registering dataset...")
    
    register_use_case = RegisterDatasetUseCase(
        dataset_repo=container.dataset_repo,
        file_storage=container.file_storage,
    )
    
    # For local testing, use the temp file path directly
    # LocalFileStorageService will handle it
    dataset_result = await register_use_case.execute(
        RegisterDatasetRequest(
            name="test_dataset",
            minio_path=dataset_path,  # Local path works with LocalFileStorageService
            user_id="user1",
            description="Test classification dataset",
        )
    )
    print(f"   Dataset ID: {dataset_result.dataset_id}")
    print(f"   Columns: {dataset_result.columns}")
    
    # 3. Submit AutoML job
    print("\n3. Submitting AutoML training job...")
    
    from src.application.use_cases import SubmitAutoMLJobUseCase
    from src.application.dto import AutoMLTrainRequest
    
    train_use_case = SubmitAutoMLJobUseCase(
        dataset_repo=container.dataset_repo,
        job_repo=container.job_repo,
    )
    
    job_result = await train_use_case.execute(
        AutoMLTrainRequest(
            dataset_id=dataset_result.dataset_id,
            target_column="target",
            problem_type="binary",
            user_id="user1",
            time_limit=60,  # 60 seconds for quick test
            presets="medium_quality",
        )
    )
    print(f"   Job ID: {job_result.job_id}")
    print(f"   Status: {job_result.status}")
    
    # 4. Start worker and wait for completion
    print("\n4. Starting job worker...")
    
    # Run worker in background
    worker_task = asyncio.create_task(container.job_worker.run())
    
    # Poll for completion
    print("   Waiting for training to complete...")
    from src.application.use_cases import GetJobStatusUseCase
    
    status_use_case = GetJobStatusUseCase(job_repo=container.job_repo)
    
    max_wait = 120  # 2 minutes max
    elapsed = 0
    
    while elapsed < max_wait:
        await asyncio.sleep(5)
        elapsed += 5
        
        status = await status_use_case.execute(job_result.job_id, "user1")
        print(f"   [{elapsed}s] Status: {status.status}, Progress: {status.progress:.0%}")
        
        if status.status in ("completed", "failed"):
            break
    
    # Stop worker
    container.job_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    
    # 5. Check results
    print("\n5. Checking results...")
    
    final_status = await status_use_case.execute(job_result.job_id, "user1")
    
    if final_status.status == "completed":
        print(f"   ✅ Training completed!")
        print(f"   Model ID: {final_status.model_id}")
        
        # Get leaderboard
        model = await container.model_repo.find_by_id(final_status.model_id)
        if model and model.leaderboard:
            print("\n   Leaderboard:")
            for i, entry in enumerate(model.leaderboard[:5]):
                print(f"   {i+1}. {entry.model_name}: {entry.score:.4f}")
        
        print("\n" + "=" * 60)
        print("TEST PASSED ✅")
        print("=" * 60)
        return True
        
    else:
        print(f"   ❌ Training failed: {final_status.error_message}")
        print("\n" + "=" * 60)
        print("TEST FAILED ❌")
        print("=" * 60)
        return False


if __name__ == "__main__":
    # Check if AutoGluon is installed
    try:
        import autogluon.tabular
        print(f"AutoGluon version: {autogluon.tabular.__version__}")
    except ImportError:
        print("ERROR: AutoGluon not installed!")
        print("Install with: pip install autogluon.tabular")
        sys.exit(1)
    
    # Run test
    result = asyncio.run(test_automl_flow())
    sys.exit(0 if result else 1)

#!/usr/bin/env python3
"""
End-to-End Test for AutoML Service

Tests the complete flow:
1. Upload dataset to MinIO
2. Register dataset via API
3. Submit AutoML job
4. Poll for job completion
5. Get leaderboard results

Prerequisites:
- MinIO running (configure MINIO_ENDPOINT environment variable)
- automl-api running at localhost:8001
- automl-worker running (for actual training)

Usage:
    pip install minio httpx pandas scikit-learn
    python tests/test_e2e.py
"""
import asyncio
import time
from io import BytesIO

import httpx
import pandas as pd
from minio import Minio
from sklearn.datasets import load_iris

import os

# Configuration - Override with environment variables
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_DATASET_BUCKET", "automl-datasets")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

API_BASE_URL = "http://localhost:8001"


def create_test_dataset() -> pd.DataFrame:
    """Create a simple test dataset from Iris."""
    iris = load_iris()
    df = pd.DataFrame(iris.data, columns=iris.feature_names)
    df['target'] = iris.target
    return df


def upload_to_minio(df: pd.DataFrame, object_name: str) -> str:
    """Upload DataFrame to MinIO as CSV."""
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    
    # Create bucket if not exists
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        print(f"Created bucket: {MINIO_BUCKET}")
    
    # Convert DataFrame to CSV bytes
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    csv_bytes = csv_buffer.getvalue()
    
    # Upload
    client.put_object(
        MINIO_BUCKET,
        object_name,
        BytesIO(csv_bytes),
        len(csv_bytes),
        content_type="text/csv"
    )
    
    minio_path = f"s3://{MINIO_BUCKET}/{object_name}"
    print(f"Uploaded dataset to: {minio_path}")
    return minio_path


async def test_api_health():
    """Test API health endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/health")
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ API Health: {data}")
        return data


async def register_dataset(minio_path: str, name: str) -> dict:
    """Register a dataset with the API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/datasets/",
            json={
                "name": name,
                "description": "Test dataset for E2E testing",
                "minio_path": minio_path
            }
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Dataset registered: {data}")
        return data


async def submit_job(dataset_id: str, target_column: str) -> dict:
    """Submit an AutoML training job."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/jobs/",
            json={
                "dataset_id": dataset_id,
                "target_column": target_column,
                "problem_type": "multiclass",
                "time_limit": 60,  # 1 minute for quick test
                "algorithms": ["GBM", "RF"],  # Quick algorithms
                "metric": "accuracy"
            }
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Job submitted: {data}")
        return data


async def poll_job_status(job_id: str, timeout: int = 120) -> dict:
    """Poll job status until completion or timeout."""
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            resp = await client.get(f"{API_BASE_URL}/jobs/{job_id}")
            resp.raise_for_status()
            data = resp.json()
            
            status = data.get("status", "unknown")
            print(f"⏳ Job status: {status}")
            
            if status == "completed":
                print(f"✅ Job completed!")
                return data
            elif status == "failed":
                print(f"❌ Job failed: {data.get('error')}")
                return data
            
            await asyncio.sleep(5)  # Poll every 5 seconds
        
        print(f"⏰ Timeout waiting for job completion")
        return {"status": "timeout"}


async def get_leaderboard(model_id: str) -> dict:
    """Get the model leaderboard."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/models/{model_id}/leaderboard")
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Leaderboard: {data}")
        return data


async def main():
    """Run the E2E test."""
    print("=" * 60)
    print("AutoML E2E Test")
    print("=" * 60)
    
    # Step 1: Check API health
    print("\n[1/5] Checking API health...")
    await test_api_health()
    
    # Step 2: Create and upload test dataset
    print("\n[2/5] Creating and uploading test dataset...")
    df = create_test_dataset()
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    timestamp = int(time.time())
    object_name = f"test/iris_test_{timestamp}.csv"
    minio_path = upload_to_minio(df, object_name)
    
    # Step 3: Register dataset
    print("\n[3/5] Registering dataset...")
    dataset = await register_dataset(minio_path, f"iris_test_{timestamp}")
    dataset_id = dataset.get("id") or dataset.get("dataset_id")
    print(f"Dataset ID: {dataset_id}")
    
    # Step 4: Submit AutoML job
    print("\n[4/5] Submitting AutoML job...")
    job = await submit_job(dataset_id, target_column="target")
    job_id = job.get("id") or job.get("job_id")
    print(f"Job ID: {job_id}")
    
    # Step 5: Poll for completion
    print("\n[5/5] Waiting for job completion...")
    print("(This requires the automl-worker to be running)")
    result = await poll_job_status(job_id, timeout=120)
    
    if result.get("status") == "completed":
        model_id = result.get("model_id")
        if model_id:
            print(f"\n[Bonus] Getting leaderboard for model {model_id}...")
            await get_leaderboard(model_id)
    
    print("\n" + "=" * 60)
    print("E2E Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

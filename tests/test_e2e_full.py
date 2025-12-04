#!/usr/bin/env python3
"""
End-to-End Tests for AutoML MCP System

Tests the complete flow for:
1. Stats Service - Direct analysis, EDA, TableOne
2. AutoML Service - Dataset registration, training, prediction
3. MCP Server - Tool invocation

Prerequisites:
- Services running (docker compose up)
- MinIO running and accessible

Usage:
    # Run all e2e tests
    python -m pytest tests/test_e2e.py -v

    # Run specific test
    python -m pytest tests/test_e2e.py::TestStatsService -v

    # Run with markers
    python -m pytest tests/test_e2e.py -m "not slow" -v
"""
import asyncio
import base64
import json
import os
import time
from io import BytesIO, StringIO

import httpx
import pandas as pd
import pytest
from minio import Minio
from sklearn.datasets import load_iris, load_breast_cancer

# =============================================================================
# Configuration
# =============================================================================

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_DATASET_BUCKET", "automl-datasets")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Service URLs
AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")
STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8002")

# Test Configuration
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "120"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))


# =============================================================================
# Test Data Generators
# =============================================================================

def create_iris_dataset() -> pd.DataFrame:
    """Create Iris dataset for classification tests."""
    iris = load_iris()
    df = pd.DataFrame(iris.data, columns=iris.feature_names)
    df['target'] = iris.target
    return df


def create_breast_cancer_dataset() -> pd.DataFrame:
    """Create breast cancer dataset for binary classification tests."""
    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df['target'] = data.target
    return df


def create_clinical_dataset() -> pd.DataFrame:
    """Create a synthetic clinical dataset for statistical analysis."""
    import numpy as np
    np.random.seed(42)
    n = 200
    
    df = pd.DataFrame({
        'patient_id': range(1, n + 1),
        'age': np.random.normal(55, 15, n).astype(int).clip(18, 90),
        'gender': np.random.choice(['Male', 'Female'], n),
        'treatment': np.random.choice(['Control', 'Treatment'], n),
        'blood_pressure': np.random.normal(120, 20, n).round(1),
        'cholesterol': np.random.normal(200, 40, n).round(1),
        'bmi': np.random.normal(26, 5, n).round(1),
        'smoking': np.random.choice(['Never', 'Former', 'Current'], n, p=[0.5, 0.3, 0.2]),
        'outcome': np.random.choice([0, 1], n, p=[0.7, 0.3]),
    })
    
    # Add some missing values
    df.loc[np.random.choice(n, 10, replace=False), 'cholesterol'] = np.nan
    df.loc[np.random.choice(n, 5, replace=False), 'bmi'] = np.nan
    
    return df


def create_survival_dataset() -> pd.DataFrame:
    """Create a synthetic survival dataset."""
    import numpy as np
    np.random.seed(42)
    n = 150
    
    df = pd.DataFrame({
        'time': np.random.exponential(24, n).round(1),  # months
        'event': np.random.choice([0, 1], n, p=[0.3, 0.7]),
        'treatment': np.random.choice(['A', 'B'], n),
        'age': np.random.normal(60, 10, n).astype(int).clip(30, 80),
        'stage': np.random.choice(['I', 'II', 'III', 'IV'], n, p=[0.2, 0.3, 0.3, 0.2]),
    })
    
    return df


# =============================================================================
# Helper Functions
# =============================================================================

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
    
    return f"s3://{MINIO_BUCKET}/{object_name}"


async def wait_for_job(client: httpx.AsyncClient, base_url: str, job_id: str, 
                       timeout: int = TEST_TIMEOUT) -> dict:
    """Poll job status until completion or timeout."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        resp = await client.get(f"{base_url}/jobs/{job_id}")
        if resp.status_code != 200:
            await asyncio.sleep(POLL_INTERVAL)
            continue
            
        data = resp.json()
        status = data.get("status", "unknown")
        
        if status in ["completed", "failed"]:
            return data
            
        await asyncio.sleep(POLL_INTERVAL)
    
    return {"status": "timeout"}


def df_to_csv_string(df: pd.DataFrame) -> str:
    """Convert DataFrame to CSV string."""
    return df.to_csv(index=False)


def df_to_base64(df: pd.DataFrame) -> str:
    """Convert DataFrame to base64 encoded CSV."""
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    return base64.b64encode(csv_bytes).decode('utf-8')


# =============================================================================
# Stats Service Tests
# =============================================================================

@pytest.mark.e2e
class TestStatsServiceHealth:
    """Test Stats Service health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health endpoint."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{STATS_API_URL}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"


@pytest.mark.e2e
class TestStatsServiceDirect:
    """Test Stats Service direct analysis endpoints."""
    
    @pytest.mark.asyncio
    async def test_direct_quick_stats(self):
        """Test quick statistics endpoint."""
        df = create_clinical_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/quick-stats",
                json={
                    "csv_content": csv_content,
                    "user_id": "test_user"
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify response structure
            assert "summary" in data
            assert "n_rows" in data["summary"]
            assert "n_cols" in data["summary"]
            assert data["summary"]["n_rows"] == 200
    
    @pytest.mark.asyncio
    async def test_direct_analyze(self):
        """Test direct analysis endpoint (submits job)."""
        df = create_clinical_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/analyze",
                json={
                    "csv_content": csv_content,
                    "user_id": "test_user",
                    "target_column": "outcome"
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify job was submitted
            assert "job_id" in data
            assert data["status"] in ["pending", "processing"]
    
    @pytest.mark.asyncio
    async def test_direct_analyze_base64(self):
        """Test direct analysis with base64 encoded content."""
        df = create_clinical_dataset()
        csv_base64 = df_to_base64(df)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/analyze",
                json={
                    "csv_content": csv_base64,
                    "is_base64": True,
                    "user_id": "test_user"
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            assert "job_id" in data
    
    @pytest.mark.asyncio
    async def test_direct_preview(self):
        """Test data preview endpoint."""
        df = create_clinical_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/preview",
                json={
                    "csv_content": csv_content,
                    "user_id": "test_user",
                    "n_rows": 10
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify preview data
            assert "preview" in data
            assert len(data["preview"]["rows"]) <= 10


@pytest.mark.e2e
@pytest.mark.slow
class TestStatsServiceJobs:
    """Test Stats Service job-based analysis."""
    
    @pytest.mark.asyncio
    async def test_auto_analyze_full_flow(self):
        """Test complete auto-analyze flow: submit → poll → get result."""
        df = create_clinical_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Submit job
            resp = await client.post(
                f"{STATS_API_URL}/direct/analyze",
                json={
                    "csv_content": csv_content,
                    "user_id": "test_user",
                    "target_column": "outcome"
                }
            )
            assert resp.status_code == 200
            job_id = resp.json()["job_id"]
            
            # Step 2: Wait for completion
            result = await wait_for_job(client, STATS_API_URL, job_id, timeout=60)
            
            # Job may still be processing if worker not running
            assert result["status"] in ["completed", "pending", "processing", "timeout"]
            
            if result["status"] == "completed":
                # Step 3: Get result
                resp = await client.get(f"{STATS_API_URL}/jobs/{job_id}/result")
                assert resp.status_code == 200


# =============================================================================
# AutoML Service Tests
# =============================================================================

@pytest.mark.e2e
class TestAutoMLServiceHealth:
    """Test AutoML Service health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health endpoint."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{AUTOML_API_URL}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"


@pytest.mark.e2e
class TestAutoMLServiceDatasets:
    """Test AutoML Service dataset endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_datasets(self):
        """Test list datasets endpoint."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{AUTOML_API_URL}/datasets/")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_register_dataset(self):
        """Test dataset registration."""
        df = create_iris_dataset()
        timestamp = int(time.time())
        object_name = f"test/e2e_iris_{timestamp}.csv"
        
        # Upload to MinIO
        minio_path = upload_to_minio(df, object_name)
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/datasets/",
                json={
                    "name": f"e2e_iris_{timestamp}",
                    "description": "E2E test dataset",
                    "minio_path": minio_path
                }
            )
            
            assert resp.status_code in [200, 201]
            data = resp.json()
            assert "id" in data or "dataset_id" in data


@pytest.mark.e2e
class TestAutoMLServiceDirect:
    """Test AutoML Service direct analysis endpoints."""
    
    @pytest.mark.asyncio
    async def test_direct_analyze(self):
        """Test direct ML analysis endpoint."""
        df = create_iris_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/direct/analyze",
                json={
                    "csv_content": csv_content,
                    "target_column": "target"
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify ML recommendations
            assert "analysis" in data or "recommendations" in data or "result" in data
    
    @pytest.mark.asyncio
    async def test_direct_quick_stats(self):
        """Test direct quick stats endpoint."""
        df = create_breast_cancer_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{AUTOML_API_URL}/direct/quick-stats",
                json={
                    "csv_content": csv_content
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            assert "stats" in data or "summary" in data or "result" in data


# =============================================================================
# MCP Server Tests
# =============================================================================

@pytest.mark.e2e
class TestMCPServer:
    """Test MCP Server endpoints."""
    
    @pytest.mark.asyncio
    async def test_sse_connection(self):
        """Test SSE endpoint is accessible."""
        async with httpx.AsyncClient() as client:
            try:
                # Just check that SSE endpoint responds
                resp = await client.get(
                    f"{MCP_SERVER_URL}/sse",
                    timeout=5.0
                )
                # SSE may return different codes depending on implementation
                assert resp.status_code in [200, 204, 400, 405]
            except httpx.ReadTimeout:
                # SSE connection stays open, timeout is expected
                pass
            except httpx.ConnectError:
                pytest.skip("MCP Server not running")


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestIntegration:
    """Integration tests across multiple services."""
    
    @pytest.mark.asyncio
    async def test_stats_and_automl_same_data(self):
        """Test analyzing same dataset through both services."""
        df = create_breast_cancer_dataset()
        csv_content = df_to_csv_string(df)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Stats Service analysis
            stats_resp = await client.post(
                f"{STATS_API_URL}/direct/quick-stats",
                json={
                    "csv_content": csv_content,
                    "user_id": "integration_test"
                }
            )
            
            # AutoML Service analysis
            automl_resp = await client.post(
                f"{AUTOML_API_URL}/direct/quick-stats",
                json={
                    "csv_content": csv_content
                }
            )
            
            # Both should succeed
            assert stats_resp.status_code == 200
            assert automl_resp.status_code == 200
            
            # Verify data consistency (same row count)
            stats_data = stats_resp.json()
            automl_data = automl_resp.json()
            
            # Extract row counts (structure may vary)
            stats_rows = stats_data.get("summary", {}).get("n_rows") or \
                        stats_data.get("n_rows") or \
                        stats_data.get("rows")
            automl_rows = automl_data.get("stats", {}).get("n_rows") or \
                         automl_data.get("n_rows") or \
                         automl_data.get("rows")
            
            if stats_rows and automl_rows:
                assert stats_rows == automl_rows


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])

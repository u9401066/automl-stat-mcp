"""
Pytest Configuration - Shared Fixtures and Logging Setup

This module provides:
- Structured logging for all tests
- Common fixtures for sample data
- Service connection helpers
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import httpx
import pandas as pd
import pytest
import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Structured Logging Configuration
# =============================================================================

def configure_structlog():
    """Configure structlog for consistent, structured logging across tests."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Use ConsoleRenderer for colorful dev output
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            int(os.environ.get("LOG_LEVEL", "20"))  # INFO = 20
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Configure at import time
configure_structlog()

# Create logger for this module
logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Service URLs
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8002")
STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")
AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")

# Paths
WORKSPACE_ROOT = Path(__file__).parent.parent
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "sample_data"
CONTAINER_SAMPLE_DATA = "/data/sample_data"

# Test settings
TEST_USER_ID = "test_user"
DEFAULT_TIMEOUT = 30.0


# =============================================================================
# Sample Data Catalog
# =============================================================================

SAMPLE_DATASETS = {
    "iris": {
        "file": "iris.csv",
        "target": "target",
        "problem_type": "multiclass",
        "n_rows": 150,
        "n_cols": 5,
        "categorical": [],
        "numerical": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
    },
    "heart_disease": {
        "file": "heart_disease.csv",
        "target": "target",
        "problem_type": "binary",
        "n_rows": 297,
        "n_cols": 14,
        "categorical": ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"],
        "numerical": ["age", "trestbps", "chol", "thalach", "oldpeak"],
    },
    "titanic": {
        "file": "titanic.csv",
        "target": "survived",
        "problem_type": "binary",
        "n_rows": 891,
        "has_missing": True,
        "categorical": ["sex", "embarked", "pclass"],
        "numerical": ["age", "fare", "sibsp", "parch"],
    },
    "rossi_recidivism": {
        "file": "rossi_recidivism.csv",
        "time_col": "week",
        "event_col": "arrest",
        "problem_type": "survival",
        "n_rows": 432,
        "group_col": "fin",
    },
    "breast_cancer": {
        "file": "breast_cancer.csv",
        "target": "diagnosis",
        "problem_type": "binary",
        "n_rows": 569,
    },
    "diabetes": {
        "file": "diabetes.csv",
        "target": "progression",
        "problem_type": "regression",
        "n_rows": 442,
    },
    "medical_study": {
        "file": "medical_study_200.csv",
        "target": "outcome",
        "treatment_col": "treatment_group",
        "problem_type": "binary",
        "n_rows": 200,
    },
}


# =============================================================================
# Logger Fixture
# =============================================================================

@pytest.fixture
def test_logger(request):
    """Provide a structured logger bound with test context."""
    return structlog.get_logger().bind(
        test_name=request.node.name,
        test_file=request.fspath.basename if request.fspath else "unknown",
    )


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def sample_data_dir() -> Path:
    """Return path to sample data directory."""
    return SAMPLE_DATA_DIR


@pytest.fixture(scope="session")
def sample_datasets() -> Dict[str, Dict[str, Any]]:
    """Return sample datasets catalog."""
    return SAMPLE_DATASETS


@pytest.fixture
def iris_df(sample_data_dir) -> pd.DataFrame:
    """Load iris dataset as DataFrame."""
    return pd.read_csv(sample_data_dir / "iris.csv")


@pytest.fixture
def titanic_df(sample_data_dir) -> pd.DataFrame:
    """Load titanic dataset as DataFrame."""
    return pd.read_csv(sample_data_dir / "titanic.csv")


@pytest.fixture
def heart_disease_df(sample_data_dir) -> pd.DataFrame:
    """Load heart disease dataset as DataFrame."""
    return pd.read_csv(sample_data_dir / "heart_disease.csv")


@pytest.fixture
def rossi_df(sample_data_dir) -> pd.DataFrame:
    """Load rossi recidivism dataset as DataFrame."""
    return pd.read_csv(sample_data_dir / "rossi_recidivism.csv")


@pytest.fixture
def medical_study_df(sample_data_dir) -> pd.DataFrame:
    """Load medical study dataset as DataFrame."""
    return pd.read_csv(sample_data_dir / "medical_study_200.csv")


@pytest.fixture
def csv_content_iris(iris_df) -> str:
    """Return iris dataset as CSV string."""
    return iris_df.to_csv(index=False)


@pytest.fixture
def csv_content_titanic(titanic_df) -> str:
    """Return titanic dataset as CSV string."""
    return titanic_df.to_csv(index=False)


# =============================================================================
# Path Conversion Fixtures
# =============================================================================

@pytest.fixture
def container_path():
    """Convert host path to container path."""
    def _convert(filename: str) -> str:
        return f"{CONTAINER_SAMPLE_DATA}/{filename}"
    return _convert


@pytest.fixture
def host_path(sample_data_dir):
    """Get host path for a sample file."""
    def _get(filename: str) -> Path:
        return sample_data_dir / filename
    return _get


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture
async def async_client():
    """Create async HTTP client."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture
def sync_client():
    """Create sync HTTP client."""
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture
async def stats_client():
    """Create async client for stats service."""
    async with httpx.AsyncClient(
        base_url=STATS_API_URL,
        timeout=DEFAULT_TIMEOUT
    ) as client:
        yield client


@pytest.fixture
async def automl_client():
    """Create async client for automl service."""
    async with httpx.AsyncClient(
        base_url=AUTOML_API_URL,
        timeout=DEFAULT_TIMEOUT
    ) as client:
        yield client


# =============================================================================
# Service Health Fixtures
# =============================================================================

async def check_service_health(url: str, path: str = "/health") -> bool:
    """Check if a service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}{path}")
            return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture
async def services_available():
    """Check if all services are available."""
    stats_ok = await check_service_health(STATS_API_URL)
    automl_ok = await check_service_health(AUTOML_API_URL)
    
    if not (stats_ok and automl_ok):
        pytest.skip(
            f"Services not available (stats: {stats_ok}, automl: {automl_ok})"
        )
    
    return {"stats": stats_ok, "automl": automl_ok}


@pytest.fixture
async def stats_service_available():
    """Check if stats service is available."""
    if not await check_service_health(STATS_API_URL):
        pytest.skip("Stats service not available")
    return True


@pytest.fixture
async def automl_service_available():
    """Check if automl service is available."""
    if not await check_service_health(AUTOML_API_URL):
        pytest.skip("AutoML service not available")
    return True


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Data Generators
# =============================================================================

@pytest.fixture
def generate_test_df():
    """Generate test DataFrames with specific characteristics."""
    def _generate(
        n_rows: int = 100,
        n_numeric: int = 3,
        n_categorical: int = 2,
        missing_rate: float = 0.0,
        seed: int = 42,
    ) -> pd.DataFrame:
        import numpy as np
        np.random.seed(seed)
        
        data = {}
        
        # Numeric columns
        for i in range(n_numeric):
            col = f"num_{i}"
            data[col] = np.random.randn(n_rows)
            if missing_rate > 0:
                mask = np.random.random(n_rows) < missing_rate
                data[col] = np.where(mask, np.nan, data[col])
        
        # Categorical columns
        categories = ["A", "B", "C", "D"]
        for i in range(n_categorical):
            col = f"cat_{i}"
            data[col] = np.random.choice(categories, n_rows)
            if missing_rate > 0:
                mask = np.random.random(n_rows) < missing_rate
                data[col] = np.where(mask, None, data[col])
        
        # Target column
        data["target"] = np.random.choice([0, 1], n_rows)
        
        return pd.DataFrame(data)
    
    return _generate


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    yield
    # Cleanup logic can be added here
    pass

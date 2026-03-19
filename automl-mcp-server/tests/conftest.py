"""
Shared test fixtures for automl-mcp-server tests
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import numpy as np
import pandas as pd
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Data Fixtures
# =============================================================================


@pytest.fixture
def sample_numeric_df():
    """Sample DataFrame with numeric data for testing"""
    np.random.seed(42)
    return pd.DataFrame(
        {
            "group": [0] * 50 + [1] * 50,
            "value1": np.concatenate([np.random.normal(10, 2, 50), np.random.normal(15, 2, 50)]),
            "value2": np.concatenate([np.random.normal(100, 10, 50), np.random.normal(120, 10, 50)]),
            "category": np.random.choice(["A", "B", "C"], 100),
        }
    )


@pytest.fixture
def sample_binary_df():
    """Sample DataFrame for binary classification"""
    np.random.seed(42)
    n = 100
    return pd.DataFrame(
        {"feature1": np.random.randn(n), "feature2": np.random.randn(n), "target": np.random.binomial(1, 0.3, n)}
    )


@pytest.fixture
def sample_missing_df():
    """Sample DataFrame with missing values"""
    return pd.DataFrame(
        {
            "numeric": [1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0],
            "category": ["A", "B", None, "A", "B", "C", None],
            "complete": [1, 2, 3, 4, 5, 6, 7],
        }
    )


@pytest.fixture
def sample_correlation_df():
    """Sample DataFrame for correlation testing"""
    np.random.seed(42)
    n = 100
    x = np.random.randn(n)
    return pd.DataFrame(
        {
            "x": x,
            "y_positive": x * 0.8 + np.random.randn(n) * 0.2,  # Strong positive
            "y_negative": -x * 0.7 + np.random.randn(n) * 0.3,  # Strong negative
            "y_weak": x * 0.2 + np.random.randn(n) * 0.8,  # Weak
            "y_none": np.random.randn(n),  # No correlation
        }
    )


# =============================================================================
# File Fixtures
# =============================================================================


@pytest.fixture
def temp_csv_file(sample_numeric_df):
    """Create a temporary CSV file from sample_numeric_df"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_numeric_df.to_csv(f, index=False)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def temp_csv_with_missing(sample_missing_df):
    """Create a temporary CSV file with missing values"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_missing_df.to_csv(f, index=False)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_mcp():
    """Mock MCP server for tool registration"""
    mcp = Mock()
    tools = {}

    def tool_decorator():
        def inner(func):
            tools[func.__name__] = func
            return func

        return inner

    mcp.tool = tool_decorator
    mcp._registered_tools = tools
    return mcp


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for API testing"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status = Mock()
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_result_storage():
    """Mock ResultStorage for testing tools with persistence"""
    from unittest.mock import MagicMock

    mock_storage = MagicMock()
    mock_metadata = MagicMock()
    mock_metadata.result_id = "stat_test_abc12345"
    mock_metadata.minio_path = "bucket/user/test/file.json"
    mock_storage.save_result = AsyncMock(return_value=mock_metadata)

    return mock_storage


# =============================================================================
# Redis Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    import fakeredis.aioredis

    return fakeredis.aioredis.FakeRedis()


# =============================================================================
# Test Data Factories
# =============================================================================


class DataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_group_comparison_data(
        n_per_group: int = 50, n_groups: int = 2, effect_size: float = 0.5, seed: int = 42
    ) -> pd.DataFrame:
        """Create data for group comparison tests"""
        np.random.seed(seed)
        data = []
        for i in range(n_groups):
            group_data = pd.DataFrame({"group": i, "value": np.random.normal(10 + i * effect_size * 5, 2, n_per_group)})
            data.append(group_data)
        return pd.concat(data, ignore_index=True)

    @staticmethod
    def create_survival_data(n: int = 100, censoring_rate: float = 0.3, seed: int = 42) -> pd.DataFrame:
        """Create survival analysis test data"""
        np.random.seed(seed)
        time = np.random.exponential(10, n)
        event = np.random.binomial(1, 1 - censoring_rate, n)
        group = np.random.binomial(1, 0.5, n)
        return pd.DataFrame(
            {
                "time": time,
                "event": event,
                "group": group,
                "age": np.random.normal(50, 10, n),
                "score": np.random.randn(n),
            }
        )

    @staticmethod
    def create_roc_data(n: int = 200, auc: float = 0.8, seed: int = 42) -> pd.DataFrame:
        """Create ROC analysis test data"""
        np.random.seed(seed)
        y_true = np.random.binomial(1, 0.3, n)

        # Generate scores that achieve approximately target AUC
        noise = np.random.randn(n) * (1 - auc)
        y_score = y_true * auc + noise
        y_score = (y_score - y_score.min()) / (y_score.max() - y_score.min())

        return pd.DataFrame({"y_true": y_true, "y_score": y_score})


@pytest.fixture
def data_factory():
    """Provide DataFactory for tests"""
    return DataFactory


# =============================================================================
# Assertion Helpers
# =============================================================================


class Assertions:
    """Custom assertion helpers"""

    @staticmethod
    def assert_valid_result(result: dict, required_keys: list = None):
        """Assert that result has expected structure"""
        assert isinstance(result, dict)
        assert "status" in result

        if result["status"] == "success" and required_keys:
            for key in required_keys:
                assert key in result, f"Missing key: {key}"

    @staticmethod
    def assert_valid_statistics(stats: dict):
        """Assert that statistics dict is valid"""
        for key, value in stats.items():
            if isinstance(value, float):
                assert not np.isnan(value), f"{key} is NaN"
                assert not np.isinf(value), f"{key} is infinite"

    @staticmethod
    def assert_p_value_valid(p_value: float):
        """Assert that p-value is valid"""
        assert 0 <= p_value <= 1, f"Invalid p-value: {p_value}"


@pytest.fixture
def assertions():
    """Provide Assertions helper"""
    return Assertions

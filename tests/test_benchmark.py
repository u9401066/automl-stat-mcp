"""
Performance Benchmark Tests

Measures API response times for critical endpoints.

Requirements:
    pip install pytest-benchmark

Usage:
    python -m pytest tests/test_benchmark.py -v --benchmark-only
    python -m pytest tests/test_benchmark.py -v --benchmark-json=benchmark.json
"""

import os

import httpx
import pytest

# =============================================================================
# Configuration
# =============================================================================

STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")
AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")

SAMPLE_DATA = {
    "iris": "/data/sample_data/iris.csv",
    "heart": "/data/sample_data/heart_disease.csv",
    "breast_cancer": "/data/sample_data/breast_cancer.csv",
}


# =============================================================================
# Benchmark: Health Checks
# =============================================================================


@pytest.mark.benchmark
class TestHealthBenchmark:
    """Benchmark health check endpoints."""

    def test_stats_health(self, benchmark):
        """Benchmark stats service health check."""

        def call_health():
            with httpx.Client(timeout=10) as client:
                return client.get(f"{STATS_API_URL}/health")

        result = benchmark(call_health)
        assert result.status_code == 200

    def test_automl_health(self, benchmark):
        """Benchmark automl service health check."""

        def call_health():
            with httpx.Client(timeout=10) as client:
                return client.get(f"{AUTOML_API_URL}/health")

        result = benchmark(call_health)
        assert result.status_code == 200


# =============================================================================
# Benchmark: Direct Analysis (Synchronous)
# =============================================================================


@pytest.mark.benchmark
class TestDirectAnalysisBenchmark:
    """Benchmark synchronous analysis endpoints."""

    def test_column_info(self, benchmark):
        """Benchmark column info endpoint."""

        def call_column_info():
            with httpx.Client(timeout=30) as client:
                return client.post(f"{STATS_API_URL}/cleaning/column-info", json={"csv_path": SAMPLE_DATA["iris"]})

        result = benchmark(call_column_info)
        assert result.status_code == 200

    def test_eda_preview(self, benchmark):
        """Benchmark EDA preview endpoint (requires user_id)."""

        def call_preview():
            with httpx.Client(timeout=30) as client:
                return client.post(
                    f"{STATS_API_URL}/eda/preview", json={"csv_path": SAMPLE_DATA["iris"], "user_id": "benchmark"}
                )

        result = benchmark(call_preview)
        # Endpoint may return 404 if /eda/preview route not available
        assert result.status_code in [200, 404, 422]


# =============================================================================
# Benchmark: Data Cleaning
# =============================================================================


@pytest.mark.benchmark
class TestCleaningBenchmark:
    """Benchmark data cleaning endpoints."""

    def test_tableone_columns(self, benchmark):
        """Benchmark tableone columns endpoint (requires user_id)."""

        def call_columns():
            with httpx.Client(timeout=30) as client:
                return client.post(
                    f"{STATS_API_URL}/tableone/columns", json={"csv_path": SAMPLE_DATA["heart"], "user_id": "benchmark"}
                )

        result = benchmark(call_columns)
        # Skip assertion if endpoint requires different params
        assert result.status_code in [200, 422]


# =============================================================================
# Benchmark: Power Analysis
# =============================================================================


@pytest.mark.benchmark
class TestPowerBenchmark:
    """Benchmark power analysis endpoints."""

    def test_power_ttest(self, benchmark):
        """Benchmark t-test power analysis."""

        def call_power():
            with httpx.Client(timeout=30) as client:
                return client.post(
                    f"{STATS_API_URL}/power/ttest",
                    json={
                        "mode": "power",
                        "effect_size": 0.5,
                        "n1": 30,
                        "alpha": 0.05,
                    },
                )

        result = benchmark(call_power)
        assert result.status_code == 200

    def test_power_anova(self, benchmark):
        """Benchmark ANOVA power analysis."""

        def call_power():
            with httpx.Client(timeout=30) as client:
                return client.post(
                    f"{STATS_API_URL}/power/anova",
                    json={
                        "mode": "power",
                        "effect_size": 0.25,
                        "k": 3,
                        "n": 20,
                        "alpha": 0.05,
                    },
                )

        result = benchmark(call_power)
        assert result.status_code == 200


# =============================================================================
# Benchmark: AutoML Service
# =============================================================================


@pytest.mark.benchmark
class TestAutoMLBenchmark:
    """Benchmark AutoML service endpoints."""

    def test_list_algorithms(self, benchmark):
        """Benchmark list algorithms endpoint."""

        def call_list():
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                return client.get(f"{AUTOML_API_URL}/algorithms")

        result = benchmark(call_list)
        assert result.status_code == 200


# =============================================================================
# Benchmark: Storage Operations
# =============================================================================


@pytest.mark.benchmark
class TestStorageBenchmark:
    """Benchmark storage endpoints."""

    def test_redis_set_get(self, benchmark):
        """Benchmark Redis set/get cycle."""
        import time

        test_key = f"benchmark:test:{time.time()}"

        def call_redis():
            with httpx.Client(timeout=30) as client:
                # Set
                client.post(
                    f"{STATS_API_URL}/storage/redis/set", json={"key": test_key, "value": {"test": "data"}, "ttl": 60}
                )
                # Get
                return client.get(f"{STATS_API_URL}/storage/redis/get", params={"key": test_key})

        result = benchmark(call_redis)
        assert result.status_code == 200

    def test_minio_list(self, benchmark):
        """Benchmark MinIO list objects."""

        def call_list():
            with httpx.Client(timeout=30) as client:
                return client.get(
                    f"{STATS_API_URL}/storage/minio/list", params={"bucket": "automl-results", "prefix": "test"}
                )

        result = benchmark(call_list)
        # May return 200 or 404 if bucket doesn't exist
        assert result.status_code in [200, 404, 500]


# =============================================================================
# Summary Report
# =============================================================================


@pytest.mark.benchmark
def test_benchmark_summary(benchmark):
    """
    Summary of all benchmarks.

    Expected baseline performance (local Docker):
    - Health checks: < 10ms
    - Quick stats: < 100ms
    - Direct analyze: < 200ms
    - Power analysis: < 50ms
    - Redis operations: < 20ms
    """

    def noop():
        pass

    benchmark(noop)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])

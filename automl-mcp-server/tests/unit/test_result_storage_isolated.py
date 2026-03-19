"""
Isolated test for NumpyJSONEncoder and ResultStorage.

This test copies the essential code to avoid import chain issues.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

# ==============================================================================
# Copied code from result_storage.py for isolated testing
# ==============================================================================


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types and other special types."""

    def default(self, obj):
        # Handle numpy types
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        # Handle pandas types if present
        elif hasattr(obj, "item"):  # pandas scalars
            return obj.item()
        # Handle datetime
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # Handle boolean (should be handled by default, but just in case)
        elif isinstance(obj, bool):
            return obj
        # Handle bytes
        elif isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON string, handling numpy and other special types."""
    return json.dumps(data, cls=NumpyJSONEncoder, ensure_ascii=False, **kwargs)


@dataclass
class ResultMetadata:
    """Metadata for a stored analysis result"""

    result_id: str
    analysis_type: str
    user_id: str
    created_at: str
    redis_key: str
    minio_path: Optional[str] = None
    expires_at: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


class ResultStorage:
    """Simplified ResultStorage for testing."""

    def __init__(
        self,
        stats_service_url: str = "http://localhost:8003",
        automl_service_url: str = "http://localhost:8001",
        minio_bucket: str = "automl-results",
    ):
        self.stats_service_url = stats_service_url
        self.automl_service_url = automl_service_url
        self.minio_bucket = minio_bucket
        self.timeout = 30

    def _generate_result_id(self, analysis_type: str) -> str:
        """Generate a unique result ID"""
        short_uuid = uuid.uuid4().hex[:8]
        return f"stat_{analysis_type}_{short_uuid}"

    def _get_minio_path(
        self,
        user_id: str,
        analysis_type: str,
        result_id: str,
        file_format: str = "json",
    ) -> str:
        """Generate MinIO path for result storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{user_id}/{analysis_type}/{timestamp}_{result_id}.{file_format}"

    def _extract_summary(self, result: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Extract a summary from the result for quick reference"""
        summary = {}

        if analysis_type == "tableone":
            summary["n_total"] = result.get("n_total")
            summary["n_variables"] = len(result.get("variables_analyzed", []))

        elif analysis_type == "correlation":
            summary["n_variables"] = len(result.get("columns", []))
            summary["n_significant_pairs"] = len(result.get("significant_pairs", []))

        elif analysis_type == "compare_groups":
            summary["n_groups"] = result.get("n_groups")
            summary["test_used"] = result.get("main_test", {}).get("test")
            summary["p_value"] = result.get("main_test", {}).get("p_value")

        elif analysis_type == "roc":
            summary["auc"] = result.get("auc")
            summary["optimal_threshold"] = result.get("optimal_threshold")

        return summary

    def _result_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert result to Markdown format"""
        metadata = data.get("metadata", {})
        result = data.get("result", {})

        md_lines = [
            f"# Analysis Result: {metadata.get('analysis_type', 'Unknown')}",
            "",
            f"**Result ID**: {metadata.get('result_id')}",
            f"**User**: {metadata.get('user_id')}",
            f"**Created**: {metadata.get('created_at')}",
            "",
            "---",
            "",
            "## Result",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2),
            "```",
        ]

        return "\n".join(md_lines)


# ==============================================================================
# Tests
# ==============================================================================


def test_numpy_json_encoder():
    """Test NumpyJSONEncoder handles numpy types"""
    print("Testing NumpyJSONEncoder...")

    # Test int64
    data = {"value": np.int64(42)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["value"] == 42, f"Expected 42, got {parsed['value']}"
    print("✓ numpy.int64 serialization")

    # Test float64
    data = {"value": np.float64(3.14159)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert abs(parsed["value"] - 3.14159) < 0.0001
    print("✓ numpy.float64 serialization")

    # Test bool
    data = {"flag_true": np.bool_(True), "flag_false": np.bool_(False)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["flag_true"] is True
    assert parsed["flag_false"] is False
    print("✓ numpy.bool_ serialization")

    # Test array
    data = {"array": np.array([1, 2, 3, 4, 5])}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["array"] == [1, 2, 3, 4, 5]
    print("✓ numpy.ndarray serialization")

    # Test 2D array
    data = {"matrix": np.array([[1, 2], [3, 4]])}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["matrix"] == [[1, 2], [3, 4]]
    print("✓ numpy.ndarray 2D serialization")

    # Test mixed types
    data = {
        "python_int": 42,
        "python_float": 3.14,
        "python_str": "hello",
        "numpy_int": np.int64(100),
        "numpy_float": np.float64(2.718),
        "numpy_array": np.array([1, 2, 3]),
        "nested": {"numpy_bool": np.bool_(True), "list": [np.int64(1), np.int64(2)]},
    }
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["python_int"] == 42
    assert parsed["numpy_int"] == 100
    assert parsed["nested"]["numpy_bool"] is True
    print("✓ Mixed types serialization")

    # Test datetime
    data = {"timestamp": datetime(2025, 1, 1, 12, 0, 0)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["timestamp"] == "2025-01-01T12:00:00"
    print("✓ datetime serialization")

    # Test bytes
    data = {"bytes": b"hello"}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["bytes"] == "hello"
    print("✓ bytes serialization")

    # Test set
    data = {"set": {1, 2, 3}}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert sorted(parsed["set"]) == [1, 2, 3]
    print("✓ set serialization")

    print("\n✅ All NumpyJSONEncoder tests passed!")


def test_result_storage_class():
    """Test ResultStorage class methods"""
    print("\nTesting ResultStorage class...")

    storage = ResultStorage(stats_service_url="http://test:8003", minio_bucket="test-bucket")

    # Test initialization
    assert storage.stats_service_url == "http://test:8003"
    assert storage.minio_bucket == "test-bucket"
    assert storage.timeout == 30
    print("✓ Initialization")

    # Test _generate_result_id
    result_id = storage._generate_result_id("correlation")
    assert result_id.startswith("stat_correlation_")
    assert len(result_id.split("_")[-1]) == 8  # 8 char hex
    print(f"✓ Generated ID: {result_id}")

    # Test uniqueness
    ids = [storage._generate_result_id("test") for _ in range(100)]
    assert len(set(ids)) == 100
    print("✓ ID uniqueness (100 unique IDs)")

    # Test _get_minio_path
    path = storage._get_minio_path("user123", "correlation", "stat_correlation_abc12345")
    assert path.startswith("user123/correlation/")
    assert "stat_correlation_abc12345" in path
    assert path.endswith(".json")
    print(f"✓ MinIO path: {path}")

    # Test _extract_summary for different types
    # correlation
    corr_result = {"columns": ["a", "b", "c"], "significant_pairs": [("a", "b"), ("b", "c")]}
    summary = storage._extract_summary(corr_result, "correlation")
    assert summary["n_variables"] == 3
    assert summary["n_significant_pairs"] == 2
    print("✓ Summary extraction (correlation)")

    # compare_groups
    cg_result = {"n_groups": 3, "main_test": {"test": "ANOVA", "p_value": 0.001}}
    summary = storage._extract_summary(cg_result, "compare_groups")
    assert summary["n_groups"] == 3
    assert summary["test_used"] == "ANOVA"
    assert summary["p_value"] == 0.001
    print("✓ Summary extraction (compare_groups)")

    # roc
    roc_result = {"auc": 0.85, "optimal_threshold": 0.5}
    summary = storage._extract_summary(roc_result, "roc")
    assert summary["auc"] == 0.85
    assert summary["optimal_threshold"] == 0.5
    print("✓ Summary extraction (roc)")

    # tableone
    to_result = {"n_total": 500, "variables_analyzed": ["age", "gender", "bmi"]}
    summary = storage._extract_summary(to_result, "tableone")
    assert summary["n_total"] == 500
    assert summary["n_variables"] == 3
    print("✓ Summary extraction (tableone)")

    print("\n✅ All ResultStorage tests passed!")


def test_result_to_markdown():
    """Test markdown conversion"""
    print("\nTesting markdown conversion...")

    storage = ResultStorage()

    data = {
        "metadata": {
            "result_id": "stat_test_abc123",
            "analysis_type": "correlation",
            "user_id": "test_user",
            "created_at": "2025-01-01T12:00:00",
        },
        "result": {"status": "success", "data": [1, 2, 3]},
    }

    md = storage._result_to_markdown(data)

    assert "# Analysis Result: correlation" in md
    assert "**Result ID**: stat_test_abc123" in md
    assert "**User**: test_user" in md
    assert "**Created**: 2025-01-01T12:00:00" in md
    assert "```json" in md
    assert '"status": "success"' in md
    print("✓ Markdown contains expected headers and format")

    print("\n✅ Markdown conversion test passed!")


def test_result_metadata_dataclass():
    """Test ResultMetadata dataclass"""
    print("\nTesting ResultMetadata dataclass...")

    metadata = ResultMetadata(
        result_id="stat_test_abc123",
        analysis_type="correlation",
        user_id="test_user",
        created_at="2025-01-01T12:00:00",
        redis_key="stats:result:stat_test_abc123",
        minio_path="bucket/path/file.json",
        expires_at="2025-01-08T12:00:00",
        summary={"n_variables": 5},
    )

    assert metadata.result_id == "stat_test_abc123"
    assert metadata.analysis_type == "correlation"
    assert metadata.user_id == "test_user"
    assert metadata.redis_key == "stats:result:stat_test_abc123"
    assert metadata.minio_path == "bucket/path/file.json"
    assert metadata.summary["n_variables"] == 5
    print("✓ All fields accessible")

    # Test default values
    metadata2 = ResultMetadata(
        result_id="test", analysis_type="test", user_id="user", created_at="now", redis_key="key"
    )
    assert metadata2.minio_path is None
    assert metadata2.expires_at is None
    assert metadata2.summary == {}
    print("✓ Default values work")

    print("\n✅ ResultMetadata tests passed!")


def test_edge_cases():
    """Test edge cases"""
    print("\nTesting edge cases...")

    # Empty data
    data = {}
    result = safe_json_dumps(data)
    assert result == "{}"
    print("✓ Empty dict serialization")

    # Deeply nested numpy
    data = {"level1": {"level2": {"level3": {"value": np.float64(1.5)}}}}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["level1"]["level2"]["level3"]["value"] == 1.5
    print("✓ Deeply nested numpy serialization")

    # List of numpy arrays
    data = {"arrays": [np.array([1, 2]), np.array([3, 4])]}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["arrays"] == [[1, 2], [3, 4]]
    print("✓ List of numpy arrays")

    # Unicode in strings
    data = {"chinese": "中文測試", "emoji": "🎉"}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["chinese"] == "中文測試"
    assert parsed["emoji"] == "🎉"
    print("✓ Unicode support")

    # Large integers
    data = {"big": np.int64(9223372036854775807)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed["big"] == 9223372036854775807
    print("✓ Large integer handling")

    print("\n✅ Edge case tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Running result_storage isolated tests")
    print("=" * 60)

    test_numpy_json_encoder()
    test_result_storage_class()
    test_result_to_markdown()
    test_result_metadata_dataclass()
    test_edge_cases()

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)

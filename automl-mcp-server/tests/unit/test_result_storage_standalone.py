"""
Standalone test for NumpyJSONEncoder and utility functions.

This test can run locally without Docker.
"""
import json
import os
import sys

# Add src path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Create mock modules to avoid import errors
import types

# Mock httpx
httpx_mock = types.ModuleType('httpx')
httpx_mock.AsyncClient = object
sys.modules['httpx'] = httpx_mock

# Mock mcp modules
mcp_mock = types.ModuleType('mcp')
mcp_server_mock = types.ModuleType('mcp.server')
mcp_server_fastmcp_mock = types.ModuleType('mcp.server.fastmcp')
mcp_server_fastmcp_mock.FastMCP = object
sys.modules['mcp'] = mcp_mock
sys.modules['mcp.server'] = mcp_server_mock
sys.modules['mcp.server.fastmcp'] = mcp_server_fastmcp_mock

import numpy as np  # noqa: E402


def test_numpy_json_encoder():
    """Test NumpyJSONEncoder handles numpy types"""
    # Import after mocking
    from infrastructure.mcp.handlers.result_storage import safe_json_dumps

    print("Testing NumpyJSONEncoder...")

    # Test int64
    data = {'value': np.int64(42)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed['value'] == 42, f"Expected 42, got {parsed['value']}"
    print("✓ numpy.int64 serialization")

    # Test float64
    data = {'value': np.float64(3.14159)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert abs(parsed['value'] - 3.14159) < 0.0001
    print("✓ numpy.float64 serialization")

    # Test bool
    data = {'flag_true': np.bool_(True), 'flag_false': np.bool_(False)}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed['flag_true'] is True
    assert parsed['flag_false'] is False
    print("✓ numpy.bool_ serialization")

    # Test array
    data = {'array': np.array([1, 2, 3, 4, 5])}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed['array'] == [1, 2, 3, 4, 5]
    print("✓ numpy.ndarray serialization")

    # Test 2D array
    data = {'matrix': np.array([[1, 2], [3, 4]])}
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed['matrix'] == [[1, 2], [3, 4]]
    print("✓ numpy.ndarray 2D serialization")

    # Test mixed types
    data = {
        'python_int': 42,
        'python_float': 3.14,
        'python_str': 'hello',
        'numpy_int': np.int64(100),
        'numpy_float': np.float64(2.718),
        'numpy_array': np.array([1, 2, 3]),
        'nested': {
            'numpy_bool': np.bool_(True),
            'list': [np.int64(1), np.int64(2)]
        }
    }
    result = safe_json_dumps(data)
    parsed = json.loads(result)
    assert parsed['python_int'] == 42
    assert parsed['numpy_int'] == 100
    assert parsed['nested']['numpy_bool'] is True
    print("✓ Mixed types serialization")

    print("\n✅ All NumpyJSONEncoder tests passed!")


def test_result_storage_class():
    """Test ResultStorage class methods"""
    from infrastructure.mcp.handlers.result_storage import ResultStorage

    print("\nTesting ResultStorage class...")

    storage = ResultStorage(
        stats_service_url="http://test:8003",
        minio_bucket="test-bucket"
    )

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
    corr_result = {
        "columns": ["a", "b", "c"],
        "significant_pairs": [("a", "b"), ("b", "c")]
    }
    summary = storage._extract_summary(corr_result, "correlation")
    assert summary["n_variables"] == 3
    assert summary["n_significant_pairs"] == 2
    print("✓ Summary extraction (correlation)")

    # compare_groups
    cg_result = {
        "n_groups": 3,
        "main_test": {"test": "ANOVA", "p_value": 0.001}
    }
    summary = storage._extract_summary(cg_result, "compare_groups")
    assert summary["n_groups"] == 3
    assert summary["test_used"] == "ANOVA"
    assert summary["p_value"] == 0.001
    print("✓ Summary extraction (compare_groups)")

    # roc
    roc_result = {
        "auc": 0.85,
        "optimal_threshold": 0.5
    }
    summary = storage._extract_summary(roc_result, "roc")
    assert summary["auc"] == 0.85
    assert summary["optimal_threshold"] == 0.5
    print("✓ Summary extraction (roc)")

    print("\n✅ All ResultStorage tests passed!")


def test_result_to_markdown():
    """Test markdown conversion"""
    from infrastructure.mcp.handlers.result_storage import ResultStorage

    print("\nTesting markdown conversion...")

    storage = ResultStorage()

    data = {
        "metadata": {
            "result_id": "stat_test_abc123",
            "analysis_type": "correlation",
            "user_id": "test_user",
            "created_at": "2025-01-01T12:00:00"
        },
        "result": {
            "status": "success",
            "data": [1, 2, 3]
        }
    }

    md = storage._result_to_markdown(data)

    assert "# Analysis Result: correlation" in md
    assert "**Result ID**: stat_test_abc123" in md
    assert "**User**: test_user" in md
    assert "```json" in md
    print("✓ Markdown contains expected headers and format")

    print("\n✅ Markdown conversion test passed!")


def test_singleton():
    """Test get_result_storage singleton"""
    from infrastructure.mcp.handlers import result_storage as rs

    print("\nTesting singleton pattern...")

    # Reset singleton
    rs._result_storage = None

    storage1 = rs.get_result_storage()
    storage2 = rs.get_result_storage()

    assert storage1 is storage2
    print("✓ Singleton returns same instance")

    print("\n✅ Singleton test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Running result_storage standalone tests")
    print("=" * 60)

    test_numpy_json_encoder()
    test_result_storage_class()
    test_result_to_markdown()
    test_singleton()

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)

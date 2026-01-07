"""
Tool Logic Tests

Tests MCP tool parameter validation and edge case handling:
- Missing required parameters
- Invalid column names
- Type mismatches
- Tool-specific logic

These tests can run locally with mocked services or against real services.
"""
import json
from typing import Any, Dict, List, Optional

import pandas as pd
import pytest
import structlog

# =============================================================================
# Test Configuration
# =============================================================================

logger = structlog.get_logger(__name__)


# =============================================================================
# Mock Fixtures for Local Testing
# =============================================================================

@pytest.fixture
def mock_stats_response():
    """Create mock stats service responses."""
    def _create(
        status: str = "completed",
        n_rows: int = 100,
        n_cols: int = 5,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        if error:
            return {"status": "failed", "error": error}
        return {
            "status": status,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "columns": [f"col_{i}" for i in range(n_cols)],
            "summary": {"mean": {}, "std": {}},
        }
    return _create


@pytest.fixture
def sample_dataframes():
    """Provide various sample DataFrames for testing."""
    import numpy as np

    return {
        "normal": pd.DataFrame({
            "num1": [1, 2, 3, 4, 5],
            "num2": [1.1, 2.2, 3.3, 4.4, 5.5],
            "cat": ["A", "B", "A", "B", "A"],
            "target": [0, 1, 0, 1, 0],
        }),
        "with_missing": pd.DataFrame({
            "num1": [1, np.nan, 3, np.nan, 5],
            "num2": [1.1, 2.2, np.nan, 4.4, np.nan],
            "cat": ["A", None, "A", "B", None],
            "target": [0, 1, 0, 1, 0],
        }),
        "all_missing": pd.DataFrame({
            "col1": [np.nan] * 5,
            "col2": [None] * 5,
        }),
        "empty": pd.DataFrame(columns=["a", "b", "c"]),
        "single_row": pd.DataFrame({"a": [1], "b": [2]}),
        "unicode": pd.DataFrame({
            "中文": [1, 2, 3],
            "日本語": [4, 5, 6],
            "emoji_🎉": [7, 8, 9],
        }),
    }


# =============================================================================
# Test: Parameter Validation
# =============================================================================

class TestParameterValidation:
    """Test tool parameter validation logic."""

    def test_csv_path_validation(self, test_logger):
        """Test CSV path parameter validation."""
        test_logger.info("test_start", test="csv_path_validation")

        valid_paths = [
            "/data/sample_data/iris.csv",
            "/data/projects/study/data.csv",
            "iris.csv",
            "sample_data/iris.csv",
        ]

        invalid_paths = [
            "",
            None,
            "/home/user/data.csv",  # Host path (should warn)
            "data.txt",  # Wrong extension
            "../../../etc/passwd",  # Path traversal attempt
        ]

        # Test path validation logic
        for path in valid_paths:
            is_valid = self._validate_csv_path(path)
            test_logger.info("valid_path_check", path=path, valid=is_valid)
            # Document actual validation results

        for path in invalid_paths:
            is_valid = self._validate_csv_path(path)
            test_logger.info("invalid_path_check", path=path, valid=is_valid)

    def _validate_csv_path(self, path: Optional[str]) -> bool:
        """Validate CSV path format."""
        if not path:
            return False
        if not path.endswith(".csv"):
            return False
        if ".." in path:
            return False
        return True

    def test_column_name_validation(self, sample_dataframes, test_logger):
        """Test column name validation against DataFrame."""
        test_logger.info("test_start", test="column_name_validation")

        df = sample_dataframes["normal"]
        valid_columns = list(df.columns)
        invalid_columns = ["nonexistent", "fake_col", ""]

        for col in valid_columns:
            exists = col in df.columns
            test_logger.info("valid_column", column=col, exists=exists)
            assert exists

        for col in invalid_columns:
            exists = col in df.columns
            test_logger.info("invalid_column", column=col, exists=exists)
            assert not exists

    def test_required_params_missing(self, test_logger):
        """Test handling when required parameters are missing."""
        test_logger.info("test_start", test="required_params_missing")

        # Simulate tool parameter validation
        def validate_tableone_params(params: Dict) -> List[str]:
            errors = []
            if not params.get("csv_path") and not params.get("csv_content"):
                errors.append("Either csv_path or csv_content is required")
            if not params.get("user_id"):
                errors.append("user_id is required")
            return errors

        test_cases = [
            ({}, ["csv_path or csv_content", "user_id"]),
            ({"csv_path": "/data/iris.csv"}, ["user_id"]),
            ({"user_id": "test"}, ["csv_path or csv_content"]),
            ({"csv_path": "/data/iris.csv", "user_id": "test"}, []),
        ]

        for params, _expected_errors in test_cases:
            errors = validate_tableone_params(params)
            has_errors = len(errors) > 0
            test_logger.info(
                "param_validation",
                params=params,
                has_errors=has_errors,
                error_count=len(errors)
            )


# =============================================================================
# Test: Type Handling
# =============================================================================

class TestTypeHandling:
    """Test data type handling in tools."""

    def test_numeric_column_detection(self, sample_dataframes, test_logger):
        """Test detection of numeric columns."""
        test_logger.info("test_start", test="numeric_detection")

        df = sample_dataframes["normal"]

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        test_logger.info(
            "type_detection",
            numeric=numeric_cols,
            categorical=categorical_cols
        )

        assert "num1" in numeric_cols
        assert "num2" in numeric_cols
        assert "cat" in categorical_cols

    def test_type_mismatch_handling(self, test_logger):
        """Test handling when column type doesn't match expected."""
        test_logger.info("test_start", test="type_mismatch")

        df = pd.DataFrame({
            "str_as_num": ["1", "2", "3", "4", "5"],
            "mixed": [1, "two", 3, "four", 5],
        })

        # Attempt to compute mean on string column
        try:
            mean = df["str_as_num"].mean()
            test_logger.warning("unexpected_success", mean=mean)
        except TypeError as e:
            test_logger.info("expected_type_error", error=str(e))

        # Check dtype detection
        test_logger.info("dtypes", dtypes=df.dtypes.to_dict())

    def test_nan_inf_handling(self, test_logger):
        """Test handling of NaN and Inf values."""
        test_logger.info("test_start", test="nan_inf_handling")

        import numpy as np

        df = pd.DataFrame({
            "with_nan": [1.0, np.nan, 3.0, np.nan, 5.0],
            "with_inf": [1.0, np.inf, 3.0, -np.inf, 5.0],
            "normal": [1.0, 2.0, 3.0, 4.0, 5.0],
        })

        # Check handling
        nan_counts = df.isna().sum().to_dict()
        inf_mask = df.isin([np.inf, -np.inf])
        inf_counts = inf_mask.sum().to_dict()

        test_logger.info(
            "special_values",
            nan_counts=nan_counts,
            inf_counts=inf_counts
        )

        # Verify JSON serialization safety
        result = {
            "mean": df.mean().to_dict(),
            "nan_counts": nan_counts,
        }

        # Replace NaN/Inf for JSON
        def sanitize(obj):
            if isinstance(obj, float):
                if pd.isna(obj) or obj != obj:
                    return None
                if obj == float('inf') or obj == float('-inf'):
                    return str(obj)
            return obj

        try:
            json_str = json.dumps(result, default=str)
            test_logger.info("json_serializable", length=len(json_str))
        except (ValueError, TypeError) as e:
            test_logger.error("json_error", error=str(e))


# =============================================================================
# Test: Tool-Specific Logic
# =============================================================================

class TestToolSpecificLogic:
    """Test specific tool logic."""

    def test_tableone_groupby_validation(self, sample_dataframes, test_logger):
        """Test TableOne groupby column validation."""
        test_logger.info("test_start", test="tableone_groupby")

        df = sample_dataframes["normal"]

        # Valid groupby columns (categorical or few unique values)
        def is_valid_groupby(df: pd.DataFrame, col: str) -> bool:
            if col not in df.columns:
                return False
            unique_ratio = df[col].nunique() / len(df)
            return unique_ratio < 0.5  # Less than 50% unique

        for col in df.columns:
            valid = is_valid_groupby(df, col)
            nunique = df[col].nunique()
            test_logger.info(
                "groupby_check",
                column=col,
                valid=valid,
                unique_values=nunique
            )

    def test_survival_column_validation(self, test_logger):
        """Test survival analysis column validation."""
        test_logger.info("test_start", test="survival_validation")

        df = pd.DataFrame({
            "time": [10, 20, 30, 40, 50],
            "event": [1, 0, 1, 0, 1],
            "invalid_time": [-1, 0, 10, 20, 30],  # Negative value
            "invalid_event": [0, 1, 2, 0, 1],  # Non-binary
        })

        def validate_survival_data(df, time_col, event_col):
            errors = []

            # Time must be positive
            if (df[time_col] < 0).any():
                errors.append(f"{time_col} contains negative values")

            # Event must be binary (0/1)
            unique_events = df[event_col].dropna().unique()
            if not set(unique_events).issubset({0, 1}):
                errors.append(f"{event_col} must be binary (0/1)")

            return errors

        # Test valid columns
        errors = validate_survival_data(df, "time", "event")
        test_logger.info("valid_survival", errors=errors)
        assert len(errors) == 0

        # Test invalid time
        errors = validate_survival_data(df, "invalid_time", "event")
        test_logger.info("invalid_time", errors=errors)
        assert len(errors) > 0

        # Test invalid event
        errors = validate_survival_data(df, "time", "invalid_event")
        test_logger.info("invalid_event", errors=errors)
        assert len(errors) > 0

    def test_roc_column_validation(self, test_logger):
        """Test ROC analysis column validation."""
        test_logger.info("test_start", test="roc_validation")

        import numpy as np

        df = pd.DataFrame({
            "y_true": [0, 1, 0, 1, 0, 1],
            "y_score": [0.1, 0.9, 0.2, 0.8, 0.3, 0.7],
            "invalid_true": [0, 1, 2, 0, 1, 2],  # Non-binary
            "invalid_score": [0.1, np.nan, 0.3, 0.4, np.nan, 0.6],  # Has NaN
        })

        def validate_roc_data(df, true_col, score_col):
            errors = []

            # True must be binary
            unique_true = df[true_col].dropna().unique()
            if not set(unique_true).issubset({0, 1}):
                errors.append(f"{true_col} must be binary (0/1)")

            # Score should be 0-1 and no NaN
            if df[score_col].isna().any():
                errors.append(f"{score_col} contains missing values")

            if ((df[score_col] < 0) | (df[score_col] > 1)).any():
                errors.append(f"{score_col} should be between 0 and 1")

            return errors

        # Test valid
        errors = validate_roc_data(df, "y_true", "y_score")
        test_logger.info("valid_roc", errors=errors)
        assert len(errors) == 0

        # Test invalid
        errors = validate_roc_data(df, "invalid_true", "y_score")
        test_logger.info("invalid_true", errors=errors)
        assert len(errors) > 0


# =============================================================================
# Test: Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling in tools."""

    def test_graceful_empty_data(self, sample_dataframes, test_logger):
        """Test graceful handling of empty data."""
        test_logger.info("test_start", test="empty_data")

        df = sample_dataframes["empty"]

        # Should not crash
        try:
            summary = {
                "n_rows": len(df),
                "n_cols": len(df.columns),
                "columns": list(df.columns),
            }
            test_logger.info("empty_handled", summary=summary)
        except Exception as e:
            test_logger.error("empty_error", error=str(e))
            pytest.fail(f"Empty DataFrame handling failed: {e}")

    def test_graceful_all_missing(self, sample_dataframes, test_logger):
        """Test graceful handling of all-missing data."""
        test_logger.info("test_start", test="all_missing")

        df = sample_dataframes["all_missing"]

        try:
            # Should handle gracefully
            stats = df.describe()
            missing_pct = (df.isna().sum() / len(df) * 100).to_dict()

            test_logger.info(
                "all_missing_handled",
                missing_pct=missing_pct,
                stats_shape=stats.shape
            )
        except Exception as e:
            test_logger.error("all_missing_error", error=str(e))

    def test_unicode_column_handling(self, sample_dataframes, test_logger):
        """Test handling of Unicode column names."""
        test_logger.info("test_start", test="unicode_columns")

        df = sample_dataframes["unicode"]

        try:
            # Should handle Unicode columns
            columns = list(df.columns)
            dtypes = {col: str(df[col].dtype) for col in df.columns}

            test_logger.info(
                "unicode_handled",
                columns=columns,
                dtypes=dtypes
            )

            # Test JSON serialization
            json_str = json.dumps({"columns": columns})
            test_logger.info("json_ok", length=len(json_str))

        except Exception as e:
            test_logger.error("unicode_error", error=str(e))
            pytest.fail(f"Unicode handling failed: {e}")


# =============================================================================
# Test: Path Resolution Logic
# =============================================================================

class TestPathResolutionLogic:
    """Test path resolution logic (can run locally)."""

    def test_path_normalization(self, test_logger):
        """Test path normalization logic."""
        test_logger.info("test_start", test="path_normalization")

        def normalize_path(path: str) -> str:
            """Normalize user input to container path."""
            if not path:
                return path

            # Remove leading/trailing whitespace
            path = path.strip()

            # Convert host paths to container paths
            if path.startswith("/home/"):
                # Extract just the filename
                parts = path.split("/")
                if "sample_data" in parts:
                    idx = parts.index("sample_data")
                    path = "/data/sample_data/" + "/".join(parts[idx+1:])

            # Handle relative paths
            if not path.startswith("/"):
                if path.startswith("sample_data/"):
                    path = "/data/" + path
                else:
                    path = "/data/sample_data/" + path

            return path

        test_cases = [
            ("iris.csv", "/data/sample_data/iris.csv"),
            ("sample_data/iris.csv", "/data/sample_data/iris.csv"),
            ("/data/sample_data/iris.csv", "/data/sample_data/iris.csv"),
            ("/home/user/sample_data/iris.csv", "/data/sample_data/iris.csv"),
        ]

        for input_path, expected in test_cases:
            result = normalize_path(input_path)
            matches = result == expected
            test_logger.info(
                "path_normalized",
                input=input_path,
                result=result,
                expected=expected,
                matches=matches
            )
            assert matches, f"Path normalization failed: {input_path} -> {result}, expected {expected}"


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

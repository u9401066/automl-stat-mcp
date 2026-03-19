"""
Isolated tests for upload utilities.

Tests the column sanitization and CSV processing functions.
"""

import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ==============================================================================
# Copied helper functions for isolated testing
# ==============================================================================


def _sanitize_column_name(name: str) -> str:
    """
    Sanitize column name for safe usage in analysis.
    """
    if not name or not isinstance(name, str):
        return "unnamed"

    original = name.strip()

    # If empty after strip
    if not original:
        return "unnamed"

    # Handle "Unnamed: X" from Excel
    if original.lower().startswith("unnamed:"):
        return f"col_{original.split(':')[-1].strip()}"

    # Replace special characters with underscore (keep Chinese, alphanumeric)
    sanitized = re.sub(r"[^\w\u4e00-\u9fff]", "_", original)

    # Replace multiple underscores with single
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # If empty after sanitization, use hash of original
    if not sanitized:
        sanitized = f"col_{abs(hash(original)) % 10000}"

    return sanitized


def _create_column_mapping(original_columns: List[str]) -> Dict[str, Any]:
    """
    Create mapping from original column names to sanitized names.
    """
    mapping = {}
    reverse_mapping = {}
    changed = []
    unchanged = []

    used_names = {}

    for orig in original_columns:
        sanitized = _sanitize_column_name(orig)

        if sanitized in used_names:
            used_names[sanitized] += 1
            sanitized = f"{sanitized}_{used_names[sanitized]}"
        else:
            used_names[sanitized] = 0

        mapping[orig] = sanitized
        reverse_mapping[sanitized] = orig

        if orig != sanitized:
            changed.append((orig, sanitized))
        else:
            unchanged.append(orig)

    return {
        "mapping": mapping,
        "reverse_mapping": reverse_mapping,
        "changed_columns": changed,
        "unchanged_columns": unchanged,
        "total_columns": len(original_columns),
        "columns_renamed": len(changed),
    }


# ==============================================================================
# Tests
# ==============================================================================


class TestColumnSanitization:
    """Test column name sanitization"""

    def test_basic_names_unchanged(self):
        """Test that basic column names are unchanged"""
        test_cases = [
            "age",
            "name",
            "user_id",
            "column_123",
            "ABC",
        ]

        for name in test_cases:
            result = _sanitize_column_name(name)
            assert result == name, f"'{name}' should be unchanged, got '{result}'"

        print("✓ Basic names unchanged")

    def test_spaces_replaced(self):
        """Test that spaces are replaced with underscores"""
        test_cases = [
            ("column name", "column_name"),
            ("first name", "first_name"),
            ("  leading spaces", "leading_spaces"),
            ("trailing spaces  ", "trailing_spaces"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Spaces replaced")

    def test_special_chars_replaced(self):
        """Test that special characters are replaced"""
        test_cases = [
            ("column(1)", "column_1"),
            ("value[index]", "value_index"),
            ("price$", "price"),
            ("rate%", "rate"),
            ("user@domain", "user_domain"),
            ("path/to/column", "path_to_column"),
            ("col:name", "col_name"),
            ("semi;colon", "semi_colon"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Special chars replaced")

    def test_chinese_preserved(self):
        """Test that Chinese characters are preserved"""
        test_cases = [
            ("姓名", "姓名"),
            ("年齡", "年齡"),
            ("user_姓名", "user_姓名"),
            ("中文欄位", "中文欄位"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Chinese preserved")

    def test_unnamed_columns(self):
        """Test handling of Excel's Unnamed columns"""
        test_cases = [
            ("Unnamed: 0", "col_0"),
            ("Unnamed: 1", "col_1"),
            ("UNNAMED: 5", "col_5"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Unnamed columns handled")

    def test_multiple_underscores_collapsed(self):
        """Test that multiple underscores are collapsed"""
        test_cases = [
            ("column__name", "column_name"),
            ("a___b", "a_b"),
            ("x____y____z", "x_y_z"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Multiple underscores collapsed")

    def test_empty_and_invalid(self):
        """Test handling of empty and invalid inputs"""
        assert _sanitize_column_name("") == "unnamed"
        assert _sanitize_column_name(None) == "unnamed"
        assert _sanitize_column_name("   ") == "unnamed"

        # All special chars should result in hash-based name
        result = _sanitize_column_name("!@#$%")
        assert result.startswith("col_")

        print("✓ Empty and invalid handled")

    def test_leading_trailing_underscores_removed(self):
        """Test that leading/trailing underscores are removed"""
        test_cases = [
            ("_column", "column"),
            ("column_", "column"),
            ("_col_name_", "col_name"),
            ("__test__", "test"),
        ]

        for original, expected in test_cases:
            result = _sanitize_column_name(original)
            assert result == expected, f"'{original}' -> expected '{expected}', got '{result}'"

        print("✓ Leading/trailing underscores removed")


class TestColumnMapping:
    """Test column mapping creation"""

    def test_simple_mapping(self):
        """Test simple column mapping"""
        columns = ["id", "name", "age"]

        result = _create_column_mapping(columns)

        assert result["total_columns"] == 3
        assert result["columns_renamed"] == 0
        assert len(result["unchanged_columns"]) == 3
        print("✓ Simple mapping")

    def test_mapping_with_changes(self):
        """Test mapping with renamed columns"""
        columns = ["id", "user name", "age (years)"]

        result = _create_column_mapping(columns)

        assert result["total_columns"] == 3
        assert result["columns_renamed"] == 2
        assert "id" in result["unchanged_columns"]
        assert result["mapping"]["user name"] == "user_name"
        assert result["mapping"]["age (years)"] == "age_years"
        print("✓ Mapping with changes")

    def test_duplicate_handling(self):
        """Test handling of duplicate names after sanitization"""
        columns = ["column 1", "column-1", "column_1"]  # All become column_1

        result = _create_column_mapping(columns)

        assert result["total_columns"] == 3
        # Should have column_1, column_1_1, column_1_2
        names = list(result["mapping"].values())
        assert len(set(names)) == 3  # All unique
        print("✓ Duplicate handling")

    def test_reverse_mapping(self):
        """Test reverse mapping correctness"""
        columns = ["First Name", "Last-Name", "age"]

        result = _create_column_mapping(columns)

        # Verify reverse mapping
        for orig, sanitized in result["mapping"].items():
            assert result["reverse_mapping"][sanitized] == orig

        print("✓ Reverse mapping")


class TestCSVProcessing:
    """Test CSV processing utilities"""

    def test_dataframe_column_rename(self):
        """Test DataFrame column renaming"""
        df = pd.DataFrame(
            {
                "user name": [1, 2, 3],
                "age (years)": [25, 30, 35],
                "score%": [90, 85, 88],
            }
        )

        mapping = _create_column_mapping(df.columns.tolist())
        df_renamed = df.rename(columns=mapping["mapping"])

        assert list(df_renamed.columns) == ["user_name", "age_years", "score"]
        print("✓ DataFrame column rename")

    def test_csv_roundtrip_with_rename(self):
        """Test CSV roundtrip with column renaming"""
        df = pd.DataFrame(
            {
                "Column A": [1, 2, 3],
                "Column B": ["x", "y", "z"],
            }
        )

        mapping = _create_column_mapping(df.columns.tolist())
        df_renamed = df.rename(columns=mapping["mapping"])

        # Convert to CSV and back
        csv_content = df_renamed.to_csv(index=False)
        df_loaded = pd.read_csv(pd.io.common.StringIO(csv_content))

        assert list(df_loaded.columns) == ["Column_A", "Column_B"]
        print("✓ CSV roundtrip with rename")


class TestDataPreview:
    """Test data preview utilities"""

    def test_preview_truncation(self):
        """Test value truncation in preview"""
        max_length = 50

        short_value = "short"
        long_value = "x" * 100

        def truncate(val):
            s = str(val)
            if len(s) > max_length:
                return s[:max_length] + "..."
            return s

        assert truncate(short_value) == "short"
        assert len(truncate(long_value)) == 53  # 50 + "..."
        print("✓ Preview truncation")

    def test_row_sampling(self):
        """Test row sampling for preview"""
        df = pd.DataFrame(
            {
                "a": range(100),
                "b": range(100, 200),
            }
        )

        max_rows = 5
        preview = df.head(max_rows)

        assert len(preview) == max_rows
        assert list(preview["a"]) == [0, 1, 2, 3, 4]
        print("✓ Row sampling")

    def test_column_limiting(self):
        """Test column limiting for preview"""
        df = pd.DataFrame({f"col_{i}": [i] for i in range(20)})

        max_cols = 10
        preview_cols = df.columns[:max_cols]

        assert len(preview_cols) == 10
        assert list(preview_cols) == [f"col_{i}" for i in range(10)]
        print("✓ Column limiting")


class TestFilePathHandling:
    """Test file path handling"""

    def test_path_validation(self):
        """Test path validation patterns"""
        import os

        valid_paths = [
            "/data/sample_data/iris.csv",
            "/data/projects/my_project/data.csv",
        ]

        for path in valid_paths:
            # Check it's an absolute path
            assert os.path.isabs(path)
            # Check it has .csv extension
            assert path.endswith(".csv")

        print("✓ Path validation")

    def test_filename_extraction(self):
        """Test filename extraction from path"""
        import os

        test_cases = [
            ("/data/sample_data/iris.csv", "iris.csv"),
            ("/home/user/data/my_data.csv", "my_data.csv"),
        ]

        for path, expected in test_cases:
            filename = os.path.basename(path)
            assert filename == expected

        print("✓ Filename extraction")


class TestDataTypeParsing:
    """Test data type detection and parsing"""

    def test_numeric_detection(self):
        """Test numeric column detection"""
        df = pd.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.1, 2.2, 3.3],
                "str_col": ["a", "b", "c"],
                "mixed": [1, "two", 3],
            }
        )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        assert "int_col" in numeric_cols
        assert "float_col" in numeric_cols
        assert "str_col" not in numeric_cols
        print("✓ Numeric detection")

    def test_categorical_detection(self):
        """Test categorical column detection"""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "A", "C", "B"] * 20,  # Low cardinality
                "text": [f"text_{i}" for i in range(100)],  # High cardinality
                "id": range(100),
            }
        )

        threshold = 0.1  # <10% unique = categorical

        categorical_cols = []
        for col in df.columns:
            if df[col].dtype == "object":
                ratio = df[col].nunique() / len(df)
                if ratio < threshold:
                    categorical_cols.append(col)

        assert "category" in categorical_cols
        assert "text" not in categorical_cols
        print("✓ Categorical detection")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running upload utilities isolated tests")
    print("=" * 60)

    test_classes = [
        TestColumnSanitization(),
        TestColumnMapping(),
        TestCSVProcessing(),
        TestDataPreview(),
        TestFilePathHandling(),
        TestDataTypeParsing(),
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)

        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise

    print("\n" + "=" * 60)
    print("🎉 ALL UPLOAD UTILITY TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

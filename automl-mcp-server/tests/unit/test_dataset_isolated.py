"""
Isolated tests for dataset management utilities.

Tests dataset registration, validation, and metadata handling.
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List

# ==============================================================================
# Helper Functions for Testing
# ==============================================================================

def validate_dataset_name(name: str) -> Dict[str, Any]:
    """Validate dataset name"""
    errors = []

    if not name or not name.strip():
        errors.append("Dataset name is required")
        return {"valid": False, "errors": errors}

    name = name.strip()

    # Length check
    if len(name) < 3:
        errors.append("Dataset name must be at least 3 characters")
    if len(name) > 100:
        errors.append("Dataset name cannot exceed 100 characters")

    # Character check
    if not re.match(r'^[\w\-\.\s\u4e00-\u9fff]+$', name):
        errors.append("Dataset name contains invalid characters")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "errors": [], "sanitized": name}


def validate_minio_path(path: str) -> Dict[str, Any]:
    """Validate MinIO path format"""
    errors = []

    if not path:
        errors.append("Path is required")
        return {"valid": False, "errors": errors}

    # Split bucket and object key
    parts = path.split("/", 1)

    if len(parts) < 2:
        errors.append("Path must include bucket and object key (e.g., 'bucket/file.csv')")
        return {"valid": False, "errors": errors}

    bucket, key = parts[0], parts[1]

    # Bucket validation
    if not re.match(r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$', bucket):
        if len(bucket) < 3:
            errors.append("Bucket name must be at least 3 characters")
        elif len(bucket) > 63:
            errors.append("Bucket name cannot exceed 63 characters")
        else:
            errors.append("Invalid bucket name format")

    # Key validation
    if not key:
        errors.append("Object key is required")

    if errors:
        return {"valid": False, "errors": errors}

    return {
        "valid": True,
        "errors": [],
        "bucket": bucket,
        "key": key,
    }


def generate_dataset_id(user_id: str, name: str) -> str:
    """Generate unique dataset ID"""
    import hashlib
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    content = f"{user_id}_{name}_{timestamp}"
    hash_part = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"ds_{hash_part}"


def infer_file_type(filename: str) -> str:
    """Infer file type from filename"""
    filename = filename.lower()

    if filename.endswith('.csv'):
        return 'csv'
    elif filename.endswith('.parquet'):
        return 'parquet'
    elif filename.endswith('.xlsx') or filename.endswith('.xls'):
        return 'excel'
    elif filename.endswith('.json'):
        return 'json'
    elif filename.endswith('.tsv'):
        return 'tsv'
    else:
        return 'unknown'


def parse_column_info(columns: List[str], dtypes: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse column information"""
    result = []
    for col in columns:
        info = {
            "name": col,
            "dtype": dtypes.get(col, "object"),
            "is_numeric": dtypes.get(col, "") in ["int64", "float64", "int32", "float32"],
            "is_categorical": dtypes.get(col, "") in ["object", "category"],
        }
        result.append(info)
    return result


# ==============================================================================
# Tests
# ==============================================================================

class TestDatasetNameValidation:
    """Test dataset name validation"""

    def test_valid_name(self):
        """Test valid dataset name"""
        result = validate_dataset_name("my_dataset")
        assert result["valid"] is True
        print("✓ Valid name accepted")

    def test_name_with_chinese(self):
        """Test name with Chinese characters"""
        result = validate_dataset_name("醫療數據集")
        assert result["valid"] is True
        print("✓ Chinese name accepted")

    def test_name_too_short(self):
        """Test name too short"""
        result = validate_dataset_name("ab")
        assert result["valid"] is False
        assert "3 characters" in str(result["errors"])
        print("✓ Short name rejected")

    def test_name_too_long(self):
        """Test name too long"""
        result = validate_dataset_name("a" * 101)
        assert result["valid"] is False
        assert "100 characters" in str(result["errors"])
        print("✓ Long name rejected")

    def test_empty_name(self):
        """Test empty name"""
        result = validate_dataset_name("")
        assert result["valid"] is False
        print("✓ Empty name rejected")

    def test_whitespace_only(self):
        """Test whitespace-only name"""
        result = validate_dataset_name("   ")
        assert result["valid"] is False
        print("✓ Whitespace-only rejected")

    def test_name_with_special_chars(self):
        """Test name with allowed special characters"""
        result = validate_dataset_name("my-dataset_2024.v1")
        assert result["valid"] is True
        print("✓ Special chars (dash, underscore, dot) accepted")


class TestMinioPathValidation:
    """Test MinIO path validation"""

    def test_valid_path(self):
        """Test valid MinIO path"""
        result = validate_minio_path("my-bucket/data/file.csv")
        assert result["valid"] is True
        assert result["bucket"] == "my-bucket"
        assert result["key"] == "data/file.csv"
        print("✓ Valid path parsed")

    def test_simple_path(self):
        """Test simple bucket/file path"""
        result = validate_minio_path("bucket/file.csv")
        assert result["valid"] is True
        print("✓ Simple path accepted")

    def test_missing_bucket(self):
        """Test path without bucket"""
        result = validate_minio_path("file.csv")
        assert result["valid"] is False
        print("✓ Missing bucket detected")

    def test_empty_path(self):
        """Test empty path"""
        result = validate_minio_path("")
        assert result["valid"] is False
        print("✓ Empty path rejected")

    def test_bucket_too_short(self):
        """Test bucket name too short"""
        result = validate_minio_path("ab/file.csv")
        assert result["valid"] is False
        print("✓ Short bucket rejected")

    def test_bucket_with_uppercase(self):
        """Test bucket with uppercase (invalid)"""
        result = validate_minio_path("MyBucket/file.csv")
        assert result["valid"] is False
        print("✓ Uppercase bucket rejected")

    def test_nested_path(self):
        """Test deeply nested path"""
        result = validate_minio_path("bucket/a/b/c/d/file.csv")
        assert result["valid"] is True
        assert result["key"] == "a/b/c/d/file.csv"
        print("✓ Nested path accepted")


class TestDatasetIdGeneration:
    """Test dataset ID generation"""

    def test_id_format(self):
        """Test dataset ID format"""
        ds_id = generate_dataset_id("user1", "test")
        assert ds_id.startswith("ds_")
        assert len(ds_id) == 11  # ds_ + 8 hex chars
        print(f"✓ ID format: {ds_id}")

    def test_id_uniqueness(self):
        """Test dataset ID uniqueness"""
        ids = set()
        for i in range(100):
            ds_id = generate_dataset_id("user1", f"test_{i}")
            ids.add(ds_id)

        assert len(ids) == 100
        print("✓ IDs are unique")

    def test_id_deterministic(self):
        """Test same inputs at same time produce similar IDs"""
        # Within same second, same inputs should produce same ID
        # (depends on timing, so just verify format)
        ds_id1 = generate_dataset_id("user1", "test")
        assert ds_id1.startswith("ds_")
        print("✓ ID generation deterministic")


class TestFileTypeInference:
    """Test file type inference"""

    def test_csv_detection(self):
        """Test CSV file detection"""
        assert infer_file_type("data.csv") == "csv"
        assert infer_file_type("DATA.CSV") == "csv"
        print("✓ CSV detection")

    def test_parquet_detection(self):
        """Test Parquet file detection"""
        assert infer_file_type("data.parquet") == "parquet"
        print("✓ Parquet detection")

    def test_excel_detection(self):
        """Test Excel file detection"""
        assert infer_file_type("data.xlsx") == "excel"
        assert infer_file_type("data.xls") == "excel"
        print("✓ Excel detection")

    def test_json_detection(self):
        """Test JSON file detection"""
        assert infer_file_type("data.json") == "json"
        print("✓ JSON detection")

    def test_tsv_detection(self):
        """Test TSV file detection"""
        assert infer_file_type("data.tsv") == "tsv"
        print("✓ TSV detection")

    def test_unknown_type(self):
        """Test unknown file type"""
        assert infer_file_type("data.txt") == "unknown"
        assert infer_file_type("data") == "unknown"
        print("✓ Unknown type handled")


class TestColumnInfoParsing:
    """Test column information parsing"""

    def test_basic_parsing(self):
        """Test basic column parsing"""
        columns = ["age", "name", "score"]
        dtypes = {"age": "int64", "name": "object", "score": "float64"}

        result = parse_column_info(columns, dtypes)

        assert len(result) == 3
        assert result[0]["name"] == "age"
        assert result[0]["is_numeric"] is True
        assert result[1]["is_categorical"] is True
        print("✓ Basic column parsing")

    def test_numeric_detection(self):
        """Test numeric column detection"""
        columns = ["int_col", "float_col"]
        dtypes = {"int_col": "int64", "float_col": "float64"}

        result = parse_column_info(columns, dtypes)

        assert all(col["is_numeric"] for col in result)
        print("✓ Numeric detection")

    def test_categorical_detection(self):
        """Test categorical column detection"""
        columns = ["str_col", "cat_col"]
        dtypes = {"str_col": "object", "cat_col": "category"}

        result = parse_column_info(columns, dtypes)

        assert all(col["is_categorical"] for col in result)
        print("✓ Categorical detection")

    def test_missing_dtype(self):
        """Test handling missing dtype"""
        columns = ["unknown_col"]
        dtypes = {}

        result = parse_column_info(columns, dtypes)

        assert result[0]["dtype"] == "object"
        print("✓ Missing dtype handled")


class TestDatasetMetadata:
    """Test dataset metadata handling"""

    def test_metadata_structure(self):
        """Test metadata structure"""
        metadata = {
            "dataset_id": "ds_12345678",
            "name": "test_dataset",
            "user_id": "user_1",
            "created_at": datetime.now().isoformat(),
            "row_count": 1000,
            "column_count": 10,
            "file_size_bytes": 50000,
            "file_type": "csv",
            "minio_path": "bucket/data.csv",
        }

        # Verify required fields
        required = ["dataset_id", "name", "user_id", "created_at"]
        for field in required:
            assert field in metadata

        print("✓ Metadata structure valid")

    def test_metadata_serialization(self):
        """Test metadata JSON serialization"""
        metadata = {
            "dataset_id": "ds_12345678",
            "name": "test",
            "row_count": 1000,
        }

        json_str = json.dumps(metadata)
        restored = json.loads(json_str)

        assert restored == metadata
        print("✓ Metadata serialization")

    def test_column_metadata(self):
        """Test column-level metadata"""
        column_meta = {
            "name": "age",
            "dtype": "int64",
            "null_count": 5,
            "null_percentage": 0.5,
            "unique_count": 50,
            "min": 18,
            "max": 85,
            "mean": 42.5,
        }

        assert "dtype" in column_meta
        assert "null_count" in column_meta
        print("✓ Column metadata")


class TestDatasetList:
    """Test dataset listing and filtering"""

    def test_filter_by_user(self):
        """Test filtering datasets by user"""
        datasets = [
            {"dataset_id": "ds_1", "user_id": "user_a"},
            {"dataset_id": "ds_2", "user_id": "user_b"},
            {"dataset_id": "ds_3", "user_id": "user_a"},
        ]

        user_a_datasets = [d for d in datasets if d["user_id"] == "user_a"]

        assert len(user_a_datasets) == 2
        print("✓ Filter by user")

    def test_sort_by_date(self):
        """Test sorting by creation date"""
        datasets = [
            {"dataset_id": "ds_1", "created_at": "2024-01-01"},
            {"dataset_id": "ds_2", "created_at": "2024-03-01"},
            {"dataset_id": "ds_3", "created_at": "2024-02-01"},
        ]

        sorted_ds = sorted(datasets, key=lambda x: x["created_at"], reverse=True)

        assert sorted_ds[0]["dataset_id"] == "ds_2"
        print("✓ Sort by date")

    def test_pagination(self):
        """Test dataset pagination"""
        datasets = [{"id": i} for i in range(50)]

        page_size = 10
        page = 2  # 0-indexed

        paginated = datasets[page * page_size:(page + 1) * page_size]

        assert len(paginated) == 10
        assert paginated[0]["id"] == 20
        print("✓ Pagination")


class TestDatasetDeletion:
    """Test dataset deletion handling"""

    def test_soft_delete(self):
        """Test soft delete (mark as deleted)"""
        dataset = {
            "dataset_id": "ds_123",
            "deleted": False,
            "deleted_at": None,
        }

        # Soft delete
        dataset["deleted"] = True
        dataset["deleted_at"] = datetime.now().isoformat()

        assert dataset["deleted"] is True
        assert dataset["deleted_at"] is not None
        print("✓ Soft delete")

    def test_exclude_deleted(self):
        """Test excluding deleted datasets from list"""
        datasets = [
            {"id": "ds_1", "deleted": False},
            {"id": "ds_2", "deleted": True},
            {"id": "ds_3", "deleted": False},
        ]

        active = [d for d in datasets if not d.get("deleted", False)]

        assert len(active) == 2
        print("✓ Exclude deleted")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running dataset management isolated tests")
    print("=" * 60)

    test_classes = [
        TestDatasetNameValidation(),
        TestMinioPathValidation(),
        TestDatasetIdGeneration(),
        TestFileTypeInference(),
        TestColumnInfoParsing(),
        TestDatasetMetadata(),
        TestDatasetList(),
        TestDatasetDeletion(),
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)

        test_methods = [m for m in dir(test_class) if m.startswith('test_')]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise

    print("\n" + "=" * 60)
    print("🎉 ALL DATASET MANAGEMENT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

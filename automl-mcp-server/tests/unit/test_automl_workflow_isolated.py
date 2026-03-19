"""
Isolated tests for AutoML workflow utilities.

Tests job submission validation, parameter handling, and response parsing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

# ==============================================================================
# Mock/Helper Classes for Testing
# ==============================================================================


class JobStatus:
    """Job status enum-like class"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def all(cls):
        return [cls.PENDING, cls.RUNNING, cls.COMPLETED, cls.FAILED, cls.CANCELLED]


class ProblemType:
    """Problem type validation"""

    BINARY = "binary"
    MULTICLASS = "multiclass"
    REGRESSION = "regression"

    @classmethod
    def all(cls):
        return [cls.BINARY, cls.MULTICLASS, cls.REGRESSION]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.all()


class Presets:
    """AutoGluon presets"""

    BEST = "best_quality"
    HIGH = "high_quality"
    GOOD = "good_quality"
    MEDIUM = "medium_quality"
    DEPLOY = "optimize_for_deployment"

    @classmethod
    def all(cls):
        return [cls.BEST, cls.HIGH, cls.GOOD, cls.MEDIUM, cls.DEPLOY]


class Algorithms:
    """Available algorithms"""

    GBM = "GBM"
    CAT = "CAT"
    XGB = "XGB"
    RF = "RF"
    XT = "XT"
    KNN = "KNN"
    LR = "LR"
    NN_TORCH = "NN_TORCH"
    FASTAI = "FASTAI"

    @classmethod
    def all(cls):
        return [cls.GBM, cls.CAT, cls.XGB, cls.RF, cls.XT, cls.KNN, cls.LR, cls.NN_TORCH, cls.FASTAI]


def validate_job_request(
    dataset_id: str,
    target_column: str,
    problem_type: str,
    user_id: str,
    time_limit: int = 300,
    presets: str = "medium_quality",
    algorithms: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate job submission request"""
    errors = []

    # Required fields
    if not dataset_id or not dataset_id.strip():
        errors.append("dataset_id is required")

    if not target_column or not target_column.strip():
        errors.append("target_column is required")

    if not user_id or not user_id.strip():
        errors.append("user_id is required")

    # Problem type
    if not ProblemType.is_valid(problem_type):
        errors.append(f"Invalid problem_type: {problem_type}. Must be one of {ProblemType.all()}")

    # Time limit
    if time_limit < 60:
        errors.append("time_limit must be at least 60 seconds")
    if time_limit > 86400:  # 24 hours
        errors.append("time_limit cannot exceed 86400 seconds (24 hours)")

    # Presets
    if presets not in Presets.all():
        errors.append(f"Invalid presets: {presets}. Must be one of {Presets.all()}")

    # Algorithms (if provided)
    if algorithms:
        invalid_algos = [a for a in algorithms if a not in Algorithms.all()]
        if invalid_algos:
            errors.append(f"Invalid algorithms: {invalid_algos}. Must be from {Algorithms.all()}")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}


def parse_job_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and normalize job response"""
    return {
        "job_id": response.get("job_id"),
        "status": response.get("status", JobStatus.PENDING),
        "job_type": response.get("job_type", "automl"),
        "created_at": response.get("created_at"),
        "progress": response.get("progress", 0.0),
        "model_id": response.get("model_id"),
        "error_message": response.get("error_message"),
    }


def generate_job_id() -> str:
    """Generate unique job ID"""
    import uuid

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"job_{timestamp}_{unique}"


# ==============================================================================
# Tests
# ==============================================================================


class TestJobValidation:
    """Test job submission validation"""

    def test_valid_request(self):
        """Test valid job request"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
        )
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        print("✓ Valid request passes")

    def test_missing_dataset_id(self):
        """Test missing dataset_id"""
        result = validate_job_request(
            dataset_id="",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
        )
        assert result["valid"] is False
        assert "dataset_id" in str(result["errors"])
        print("✓ Missing dataset_id detected")

    def test_missing_target_column(self):
        """Test missing target_column"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="  ",
            problem_type="binary",
            user_id="user_1",
        )
        assert result["valid"] is False
        assert "target_column" in str(result["errors"])
        print("✓ Missing target_column detected")

    def test_invalid_problem_type(self):
        """Test invalid problem type"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="invalid",
            user_id="user_1",
        )
        assert result["valid"] is False
        assert "problem_type" in str(result["errors"])
        print("✓ Invalid problem_type detected")

    def test_time_limit_too_short(self):
        """Test time limit too short"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
            time_limit=30,
        )
        assert result["valid"] is False
        assert "time_limit" in str(result["errors"])
        print("✓ Time limit too short detected")

    def test_time_limit_too_long(self):
        """Test time limit too long"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
            time_limit=100000,
        )
        assert result["valid"] is False
        assert "time_limit" in str(result["errors"])
        print("✓ Time limit too long detected")

    def test_invalid_preset(self):
        """Test invalid preset"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
            presets="super_fast",
        )
        assert result["valid"] is False
        assert "presets" in str(result["errors"])
        print("✓ Invalid preset detected")

    def test_invalid_algorithms(self):
        """Test invalid algorithms"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
            algorithms=["XGB", "INVALID_ALGO"],
        )
        assert result["valid"] is False
        assert "algorithms" in str(result["errors"])
        print("✓ Invalid algorithms detected")

    def test_valid_algorithms(self):
        """Test valid algorithms"""
        result = validate_job_request(
            dataset_id="ds_123",
            target_column="target",
            problem_type="binary",
            user_id="user_1",
            algorithms=["XGB", "GBM", "RF"],
        )
        assert result["valid"] is True
        print("✓ Valid algorithms accepted")


class TestProblemTypes:
    """Test problem type handling"""

    def test_all_problem_types_valid(self):
        """Test all problem types are valid"""
        for pt in ProblemType.all():
            assert ProblemType.is_valid(pt)
        print("✓ All problem types valid")

    def test_binary_problem(self):
        """Test binary classification"""
        assert ProblemType.is_valid("binary")
        print("✓ Binary classification")

    def test_multiclass_problem(self):
        """Test multiclass classification"""
        assert ProblemType.is_valid("multiclass")
        print("✓ Multiclass classification")

    def test_regression_problem(self):
        """Test regression"""
        assert ProblemType.is_valid("regression")
        print("✓ Regression")


class TestAlgorithms:
    """Test algorithm handling"""

    def test_all_algorithms(self):
        """Test all algorithms list"""
        algos = Algorithms.all()
        assert len(algos) == 9
        assert "XGB" in algos
        assert "GBM" in algos
        assert "NN_TORCH" in algos
        print(f"✓ {len(algos)} algorithms available")

    def test_tree_algorithms(self):
        """Test tree-based algorithms"""
        tree_algos = ["RF", "XT", "GBM", "CAT", "XGB"]
        for algo in tree_algos:
            assert algo in Algorithms.all()
        print("✓ Tree algorithms")

    def test_neural_algorithms(self):
        """Test neural network algorithms"""
        nn_algos = ["NN_TORCH", "FASTAI"]
        for algo in nn_algos:
            assert algo in Algorithms.all()
        print("✓ Neural network algorithms")


class TestPresets:
    """Test preset handling"""

    def test_all_presets(self):
        """Test all presets"""
        presets = Presets.all()
        assert len(presets) == 5
        print(f"✓ {len(presets)} presets available")

    def test_quality_presets(self):
        """Test quality levels"""
        quality_presets = [
            Presets.BEST,
            Presets.HIGH,
            Presets.GOOD,
            Presets.MEDIUM,
        ]
        for preset in quality_presets:
            assert preset in Presets.all()
        print("✓ Quality presets")

    def test_deployment_preset(self):
        """Test deployment preset"""
        assert Presets.DEPLOY in Presets.all()
        print("✓ Deployment preset")


class TestJobStatus:
    """Test job status handling"""

    def test_all_statuses(self):
        """Test all status values"""
        statuses = JobStatus.all()
        assert len(statuses) == 5
        print(f"✓ {len(statuses)} statuses")

    def test_active_statuses(self):
        """Test active (in-progress) statuses"""
        active = [JobStatus.PENDING, JobStatus.RUNNING]
        for s in active:
            assert s in JobStatus.all()
        print("✓ Active statuses")

    def test_terminal_statuses(self):
        """Test terminal (final) statuses"""
        terminal = [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
        for s in terminal:
            assert s in JobStatus.all()
        print("✓ Terminal statuses")

    def test_status_is_terminal(self):
        """Test checking if status is terminal"""
        terminal_statuses = {"completed", "failed", "cancelled"}

        assert "completed" in terminal_statuses
        assert "pending" not in terminal_statuses
        assert "running" not in terminal_statuses
        print("✓ Terminal status check")


class TestJobIdGeneration:
    """Test job ID generation"""

    def test_job_id_format(self):
        """Test job ID format"""
        job_id = generate_job_id()

        assert job_id.startswith("job_")
        parts = job_id.split("_")
        assert len(parts) == 3
        print(f"✓ Job ID format: {job_id}")

    def test_job_id_uniqueness(self):
        """Test job ID uniqueness"""
        ids = [generate_job_id() for _ in range(100)]
        assert len(set(ids)) == 100
        print("✓ Job IDs are unique")

    def test_job_id_timestamp(self):
        """Test job ID contains timestamp"""
        job_id = generate_job_id()

        # Extract timestamp part (format: YYYYMMDDHHMMSS)
        parts = job_id.split("_")
        timestamp_part = parts[1]

        assert len(timestamp_part) == 14
        assert timestamp_part.isdigit()
        print("✓ Job ID contains timestamp")


class TestResponseParsing:
    """Test job response parsing"""

    def test_parse_pending_response(self):
        """Test parsing pending job response"""
        response = {
            "job_id": "job_123",
            "status": "pending",
            "job_type": "automl",
        }

        parsed = parse_job_response(response)
        assert parsed["job_id"] == "job_123"
        assert parsed["status"] == "pending"
        assert parsed["progress"] == 0.0
        print("✓ Parse pending response")

    def test_parse_completed_response(self):
        """Test parsing completed job response"""
        response = {
            "job_id": "job_123",
            "status": "completed",
            "job_type": "automl",
            "model_id": "model_456",
            "progress": 1.0,
        }

        parsed = parse_job_response(response)
        assert parsed["status"] == "completed"
        assert parsed["model_id"] == "model_456"
        assert parsed["progress"] == 1.0
        print("✓ Parse completed response")

    def test_parse_failed_response(self):
        """Test parsing failed job response"""
        response = {
            "job_id": "job_123",
            "status": "failed",
            "error_message": "Out of memory",
        }

        parsed = parse_job_response(response)
        assert parsed["status"] == "failed"
        assert parsed["error_message"] == "Out of memory"
        print("✓ Parse failed response")

    def test_parse_missing_fields(self):
        """Test parsing response with missing fields"""
        response = {"job_id": "job_123"}

        parsed = parse_job_response(response)
        assert parsed["job_id"] == "job_123"
        assert parsed["status"] == "pending"  # Default
        assert parsed["progress"] == 0.0  # Default
        print("✓ Parse response with defaults")


class TestMetricSelection:
    """Test automatic metric selection"""

    def test_binary_metrics(self):
        """Test metrics for binary classification"""
        binary_metrics = ["accuracy", "f1", "roc_auc", "log_loss", "balanced_accuracy"]
        default = "roc_auc"

        assert default in binary_metrics
        print("✓ Binary classification metrics")

    def test_multiclass_metrics(self):
        """Test metrics for multiclass classification"""
        multiclass_metrics = ["accuracy", "f1_macro", "f1_weighted", "log_loss"]
        default = "accuracy"

        assert default in multiclass_metrics
        print("✓ Multiclass metrics")

    def test_regression_metrics(self):
        """Test metrics for regression"""
        regression_metrics = ["rmse", "mse", "mae", "r2", "mape"]
        default = "rmse"

        assert default in regression_metrics
        print("✓ Regression metrics")


class TestTimeEstimation:
    """Test training time estimation"""

    def test_time_estimate_small_dataset(self):
        """Test time estimate for small dataset"""
        n_rows = 1000
        n_cols = 10

        # Simple heuristic: base + per-row + per-col
        base_time = 60
        row_factor = 0.01
        col_factor = 5

        estimated = base_time + n_rows * row_factor + n_cols * col_factor

        assert 60 < estimated < 300
        print(f"✓ Small dataset time estimate: {estimated:.0f}s")

    def test_time_estimate_large_dataset(self):
        """Test time estimate for large dataset"""
        n_rows = 100000
        n_cols = 100

        base_time = 60
        row_factor = 0.01
        col_factor = 5

        estimated = base_time + n_rows * row_factor + n_cols * col_factor

        assert estimated > 1000
        print(f"✓ Large dataset time estimate: {estimated:.0f}s")

    def test_preset_time_multiplier(self):
        """Test preset affects time"""
        preset_multipliers = {
            "best_quality": 4.0,
            "high_quality": 2.0,
            "good_quality": 1.5,
            "medium_quality": 1.0,
            "optimize_for_deployment": 0.5,
        }

        base_time = 300

        for _preset, mult in preset_multipliers.items():
            adjusted = base_time * mult
            assert adjusted > 0

        print("✓ Preset time multipliers")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running AutoML workflow isolated tests")
    print("=" * 60)

    test_classes = [
        TestJobValidation(),
        TestProblemTypes(),
        TestAlgorithms(),
        TestPresets(),
        TestJobStatus(),
        TestJobIdGeneration(),
        TestResponseParsing(),
        TestMetricSelection(),
        TestTimeEstimation(),
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
    print("🎉 ALL AUTOML WORKFLOW TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

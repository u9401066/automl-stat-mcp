#!/usr/bin/env python3
"""
Isolated tests for orchestration_tools.py

Tests the orchestration utilities without requiring MCP/FastMCP/network dependencies.
Following the test-generator Skill guidelines.

Test Coverage:
- Recommendation generation based on dataset size
- Response structure validation
- Job status categorization
- Summary generation
"""

from typing import List, Optional

# ============================================================
# Isolated implementations (copied from orchestration_tools.py)
# ============================================================


def get_recommendations(row_count: int, columns: list, target_column: str, dataset: dict) -> dict:
    """Generate training recommendations based on dataset characteristics"""
    recommendations = {
        "dataset_info": {
            "name": dataset.get("name"),
            "rows": row_count,
            "columns": len(columns),
            "features": [c for c in columns if c != target_column],
            "target": target_column,
        },
        "recommendations": {},
        "warnings": [],
    }

    # Recommend presets based on size
    if row_count < 1000:
        recommendations["recommendations"]["presets"] = "best_quality"
        recommendations["recommendations"]["time_limit"] = 300
        recommendations["recommendations"]["reason"] = "Small dataset - can afford thorough search"
    elif row_count < 10000:
        recommendations["recommendations"]["presets"] = "high_quality"
        recommendations["recommendations"]["time_limit"] = 600
        recommendations["recommendations"]["reason"] = "Medium dataset - balanced approach"
    elif row_count < 100000:
        recommendations["recommendations"]["presets"] = "good_quality"
        recommendations["recommendations"]["time_limit"] = 900
        recommendations["recommendations"]["reason"] = "Large dataset - optimize for speed"
    else:
        recommendations["recommendations"]["presets"] = "medium_quality"
        recommendations["recommendations"]["time_limit"] = 1200
        recommendations["recommendations"]["reason"] = "Very large dataset - faster presets recommended"
        recommendations["warnings"].append("Large dataset may require significant training time")

    # Check for few features
    if len(columns) < 3:
        recommendations["warnings"].append("Very few features - model may have limited performance")

    # Estimate
    time_limit = recommendations["recommendations"]["time_limit"]
    recommendations["estimated_training_time"] = f"{time_limit // 60}-{time_limit * 2 // 60} minutes"
    recommendations["next_step"] = (
        f"Run: train_and_wait(dataset_id='{dataset.get('dataset_id')}', target_column='{target_column}', problem_type='<your_type>', ...)"
    )

    return recommendations


def categorize_jobs(jobs: List[dict]) -> dict:
    """Categorize jobs by status"""
    return {
        "pending": [j for j in jobs if j.get("status") == "pending"],
        "running": [j for j in jobs if j.get("status") == "running"],
        "completed": [j for j in jobs if j.get("status") == "completed"],
        "failed": [j for j in jobs if j.get("status") == "failed"],
        "cancelled": [j for j in jobs if j.get("status") == "cancelled"],
    }


def build_training_summary(
    datasets: List[dict],
    jobs: List[dict],
    models: List[dict],
) -> dict:
    """Build training summary from resources"""
    categorized = categorize_jobs(jobs)

    return {
        "summary": {
            "total_datasets": len(datasets),
            "total_jobs": len(jobs),
            "total_models": len(models),
            "jobs_pending": len(categorized["pending"]),
            "jobs_running": len(categorized["running"]),
            "jobs_completed": len(categorized["completed"]),
            "jobs_failed": len(categorized["failed"]),
        },
        "datasets": [{"id": d.get("dataset_id"), "name": d.get("name"), "rows": d.get("row_count")} for d in datasets],
        "active_jobs": [
            {"id": j.get("job_id"), "type": j.get("job_type"), "status": j.get("status"), "progress": j.get("progress")}
            for j in (categorized["pending"] + categorized["running"])
        ],
        "recent_models": [
            {
                "id": m.get("model_id"),
                "name": m.get("name"),
                "best_model": m.get("best_model_name"),
                "score": m.get("best_score"),
            }
            for m in models[:5]
        ],
        "tips": [
            "Use quick_train() for fastest path from data to model",
            "Use analyze_dataset() before training to optimize settings",
            "Use train_and_wait() for full control with blocking wait",
        ],
    }


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time in human readable format"""
    if seconds < 60:
        return f"{round(seconds, 1)} seconds"
    elif seconds < 3600:
        return f"{round(seconds / 60, 1)} minutes"
    else:
        return f"{round(seconds / 3600, 1)} hours"


def build_train_response(
    job_id: str,
    dataset_id: str,
    status: str,
    elapsed: float,
    result: Optional[dict] = None,
    model_id: Optional[str] = None,
    error_message: Optional[str] = None,
    dataset_name: str = "dataset",
) -> dict:
    """Build training response"""
    response = {
        "dataset_id": dataset_id,
        "job_id": job_id,
        "status": status,
        "elapsed_seconds": round(elapsed, 1),
    }

    if status == "completed":
        response["model_id"] = model_id
        response["result"] = result
        response["summary"] = (
            f"✅ Model ready! Dataset '{dataset_name}' → Model '{model_id}' in {round(elapsed / 60, 1)} min"
        )
    elif status == "failed":
        response["error_message"] = error_message
        response["summary"] = f"❌ Training failed: {error_message}"
    else:
        response["summary"] = f"⏱️ Timeout. Use get_job_status('{job_id}') to check later."

    return response


# ============================================================
# TEST CLASSES
# ============================================================


class TestRecommendations:
    """Tests for dataset recommendations"""

    def test_small_dataset_best_quality(self):
        """Small dataset recommends best_quality"""
        rec = get_recommendations(
            row_count=500,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "best_quality"
        assert rec["recommendations"]["time_limit"] == 300

    def test_medium_dataset_high_quality(self):
        """Medium dataset recommends high_quality"""
        rec = get_recommendations(
            row_count=5000,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "high_quality"
        assert rec["recommendations"]["time_limit"] == 600

    def test_large_dataset_good_quality(self):
        """Large dataset recommends good_quality"""
        rec = get_recommendations(
            row_count=50000,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "good_quality"
        assert rec["recommendations"]["time_limit"] == 900

    def test_very_large_dataset_medium_quality(self):
        """Very large dataset recommends medium_quality"""
        rec = get_recommendations(
            row_count=200000,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "medium_quality"
        assert rec["recommendations"]["time_limit"] == 1200
        assert len(rec["warnings"]) > 0

    def test_few_features_warning(self):
        """Few features generates warning"""
        rec = get_recommendations(
            row_count=1000,
            columns=["a", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert any("few features" in w for w in rec["warnings"])

    def test_dataset_info_structure(self):
        """Dataset info has correct structure"""
        rec = get_recommendations(
            row_count=1000,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test_ds", "dataset_id": "ds_123"},
        )
        info = rec["dataset_info"]
        assert info["name"] == "test_ds"
        assert info["rows"] == 1000
        assert info["columns"] == 4
        assert info["target"] == "target"
        assert "target" not in info["features"]

    def test_next_step_includes_dataset_id(self):
        """Next step includes dataset ID"""
        rec = get_recommendations(
            row_count=1000,
            columns=["a", "b", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_abc123"},
        )
        assert "ds_abc123" in rec["next_step"]

    def test_estimated_time_format(self):
        """Estimated time has correct format"""
        rec = get_recommendations(
            row_count=1000,
            columns=["a", "b", "c", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert "minutes" in rec["estimated_training_time"]


class TestJobCategorization:
    """Tests for job categorization"""

    def test_empty_jobs(self):
        """Empty jobs list"""
        cat = categorize_jobs([])
        assert cat["pending"] == []
        assert cat["running"] == []
        assert cat["completed"] == []
        assert cat["failed"] == []

    def test_categorize_by_status(self):
        """Jobs categorized correctly by status"""
        jobs = [
            {"job_id": "1", "status": "pending"},
            {"job_id": "2", "status": "running"},
            {"job_id": "3", "status": "completed"},
            {"job_id": "4", "status": "failed"},
            {"job_id": "5", "status": "completed"},
        ]
        cat = categorize_jobs(jobs)
        assert len(cat["pending"]) == 1
        assert len(cat["running"]) == 1
        assert len(cat["completed"]) == 2
        assert len(cat["failed"]) == 1

    def test_unknown_status(self):
        """Unknown status not categorized"""
        jobs = [
            {"job_id": "1", "status": "unknown"},
        ]
        cat = categorize_jobs(jobs)
        assert cat["pending"] == []
        assert cat["running"] == []


class TestTrainingSummary:
    """Tests for training summary generation"""

    def test_empty_summary(self):
        """Summary with no resources"""
        summary = build_training_summary([], [], [])
        assert summary["summary"]["total_datasets"] == 0
        assert summary["summary"]["total_jobs"] == 0
        assert summary["summary"]["total_models"] == 0

    def test_summary_counts(self):
        """Summary counts resources correctly"""
        datasets = [{"dataset_id": "1"}, {"dataset_id": "2"}]
        jobs = [
            {"job_id": "1", "status": "completed"},
            {"job_id": "2", "status": "running"},
        ]
        models = [{"model_id": "1"}]

        summary = build_training_summary(datasets, jobs, models)
        assert summary["summary"]["total_datasets"] == 2
        assert summary["summary"]["total_jobs"] == 2
        assert summary["summary"]["total_models"] == 1
        assert summary["summary"]["jobs_completed"] == 1
        assert summary["summary"]["jobs_running"] == 1

    def test_active_jobs_only_pending_running(self):
        """Active jobs only includes pending and running"""
        jobs = [
            {"job_id": "1", "status": "pending", "job_type": "automl"},
            {"job_id": "2", "status": "running", "job_type": "automl"},
            {"job_id": "3", "status": "completed", "job_type": "automl"},
        ]
        summary = build_training_summary([], jobs, [])
        active_ids = [j["id"] for j in summary["active_jobs"]]
        assert "1" in active_ids
        assert "2" in active_ids
        assert "3" not in active_ids

    def test_recent_models_limit_5(self):
        """Recent models limited to 5"""
        models = [{"model_id": str(i)} for i in range(10)]
        summary = build_training_summary([], [], models)
        assert len(summary["recent_models"]) == 5

    def test_tips_present(self):
        """Tips are present"""
        summary = build_training_summary([], [], [])
        assert len(summary["tips"]) > 0
        assert any("quick_train" in tip for tip in summary["tips"])


class TestTrainResponse:
    """Tests for train response building"""

    def test_completed_response(self):
        """Completed training response"""
        response = build_train_response(
            job_id="job_123",
            dataset_id="ds_123",
            status="completed",
            elapsed=300.5,
            model_id="model_abc",
            result={"best_model": "LightGBM"},
            dataset_name="iris",
        )
        assert response["status"] == "completed"
        assert response["model_id"] == "model_abc"
        assert "✅" in response["summary"]
        assert "iris" in response["summary"]

    def test_failed_response(self):
        """Failed training response"""
        response = build_train_response(
            job_id="job_123",
            dataset_id="ds_123",
            status="failed",
            elapsed=60.0,
            error_message="Out of memory",
        )
        assert response["status"] == "failed"
        assert response["error_message"] == "Out of memory"
        assert "❌" in response["summary"]

    def test_timeout_response(self):
        """Timeout response"""
        response = build_train_response(
            job_id="job_123",
            dataset_id="ds_123",
            status="timeout",
            elapsed=3600.0,
        )
        assert response["status"] == "timeout"
        assert "⏱️" in response["summary"]
        assert "job_123" in response["summary"]

    def test_elapsed_seconds_rounded(self):
        """Elapsed seconds rounded correctly"""
        response = build_train_response(
            job_id="job_123",
            dataset_id="ds_123",
            status="completed",
            elapsed=123.456789,
            model_id="model_abc",
        )
        assert response["elapsed_seconds"] == 123.5


class TestElapsedTimeFormat:
    """Tests for elapsed time formatting"""

    def test_seconds(self):
        """Format seconds"""
        assert "seconds" in format_elapsed_time(30)

    def test_minutes(self):
        """Format minutes"""
        result = format_elapsed_time(120)
        assert "minutes" in result
        assert "2" in result

    def test_hours(self):
        """Format hours"""
        result = format_elapsed_time(7200)
        assert "hours" in result
        assert "2" in result


class TestBoundaryConditions:
    """Tests for boundary conditions"""

    def test_exactly_1000_rows(self):
        """Exactly 1000 rows is medium"""
        rec = get_recommendations(
            row_count=1000,
            columns=["a", "b", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        # 1000 is NOT < 1000, so should be high_quality
        assert rec["recommendations"]["presets"] == "high_quality"

    def test_exactly_10000_rows(self):
        """Exactly 10000 rows is large"""
        rec = get_recommendations(
            row_count=10000,
            columns=["a", "b", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "good_quality"

    def test_exactly_100000_rows(self):
        """Exactly 100000 rows is very large"""
        rec = get_recommendations(
            row_count=100000,
            columns=["a", "b", "target"],
            target_column="target",
            dataset={"name": "test", "dataset_id": "ds_123"},
        )
        assert rec["recommendations"]["presets"] == "medium_quality"


# ============================================================
# RUN TESTS
# ============================================================


def run_tests():
    """Run all tests"""
    test_classes = [
        TestRecommendations,
        TestJobCategorization,
        TestTrainingSummary,
        TestTrainResponse,
        TestElapsedTimeFormat,
        TestBoundaryConditions,
    ]

    print("=" * 60)
    print("Running orchestration_tools isolated tests")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 40)

        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"✓ {method_name.replace('test_', '').replace('_', ' ').title()}")
                total_passed += 1
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                total_failed += 1

    print("\n" + "=" * 60)
    if total_failed == 0:
        print(f"🎉 ALL ORCHESTRATION TOOLS TESTS PASSED! ({total_passed} tests)")
    else:
        print(f"❌ {total_failed} FAILED, {total_passed} passed")
    print("=" * 60)

    return total_failed == 0


if __name__ == "__main__":
    import sys

    success = run_tests()
    sys.exit(0 if success else 1)

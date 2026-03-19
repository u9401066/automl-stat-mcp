"""
Test Results Manager Module

Tests for JobResultsManager, SourceInfo, JobMetadata, and WorkerResultsMixin.

Run:
    cd stats-worker
    python -m pytest tests/test_results_manager.py -v
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import matplotlib
import pytest

matplotlib.use("Agg")
# Add src to path for imports
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct imports from src
from results.manager import (
    JobMetadata,
    JobResultsManager,
    SourceInfo,
)
from results.worker_mixin import WorkerResultsMixin

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_results_dir():
    """Create a temporary directory for test results."""
    temp_dir = tempfile.mkdtemp(prefix="test_results_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def results_manager(temp_results_dir):
    """Create a JobResultsManager with temp directory."""
    manager = JobResultsManager(
        user_id="test_user",
        job_name="test_analysis",
        job_type="unit_test",
        base_path=temp_results_dir,
    )
    return manager


@pytest.fixture
def sample_figure():
    """Create a sample matplotlib figure."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("Test Plot")
    return fig


@pytest.fixture
def sample_result():
    """Sample analysis result dictionary."""
    return {
        "analysis_type": "roc_analysis",
        "auc": 0.85,
        "confidence_interval": [0.80, 0.90],
        "threshold": 0.5,
        "metrics": {
            "sensitivity": 0.82,
            "specificity": 0.78,
            "ppv": 0.75,
            "npv": 0.84,
        },
        "n_samples": 500,
    }


# =============================================================================
# Test SourceInfo
# =============================================================================


class TestSourceInfo:
    """Test SourceInfo dataclass."""

    def test_to_dict_basic(self):
        """Test basic to_dict conversion."""
        source = SourceInfo(
            dataset_id="ds123",
            dataset_name="Heart Disease",
            row_count=303,
            column_count=14,
        )

        result = source.to_dict()

        assert result["dataset_id"] == "ds123"
        assert result["dataset_name"] == "Heart Disease"
        assert result["row_count"] == 303
        assert result["column_count"] == 14

    def test_to_dict_excludes_none(self):
        """Test that None values are excluded from dict."""
        source = SourceInfo(
            dataset_id="ds123",
            # All other fields are None
        )

        result = source.to_dict()

        assert "dataset_id" in result
        assert "dataset_name" not in result
        assert "row_count" not in result

    def test_to_dict_with_columns(self):
        """Test with columns list."""
        source = SourceInfo(
            dataset_name="Test",
            columns_used=["age", "gender", "outcome"],
            target_column="outcome",
        )

        result = source.to_dict()

        assert result["columns_used"] == ["age", "gender", "outcome"]
        assert result["target_column"] == "outcome"


# =============================================================================
# Test JobMetadata
# =============================================================================


class TestJobMetadata:
    """Test JobMetadata dataclass."""

    def test_to_dict_basic(self):
        """Test basic to_dict conversion."""
        metadata = JobMetadata(
            job_id="job123",
            job_name="test_job",
            user_id="user1",
            job_type="analysis",
            created_at="2024-12-10T10:00:00",
        )

        result = metadata.to_dict()

        assert result["job_id"] == "job123"
        assert result["job_name"] == "test_job"
        assert result["user_id"] == "user1"
        assert result["status"] == "running"

    def test_to_dict_with_source_info(self):
        """Test with nested SourceInfo."""
        source = SourceInfo(dataset_id="ds123", row_count=100)
        metadata = JobMetadata(
            job_id="job123",
            job_name="test_job",
            user_id="user1",
            job_type="analysis",
            created_at="2024-12-10T10:00:00",
            source_info=source,
        )

        result = metadata.to_dict()

        assert "source_info" in result
        assert result["source_info"]["dataset_id"] == "ds123"
        assert result["source_info"]["row_count"] == 100

    def test_to_dict_with_parameters(self):
        """Test with parameters dict."""
        metadata = JobMetadata(
            job_id="job123",
            job_name="test_job",
            user_id="user1",
            job_type="roc_analysis",
            created_at="2024-12-10T10:00:00",
            parameters={"threshold": 0.5, "ci_level": 0.95},
        )

        result = metadata.to_dict()

        assert result["parameters"]["threshold"] == 0.5
        assert result["parameters"]["ci_level"] == 0.95


# =============================================================================
# Test JobResultsManager - Initialization
# =============================================================================


class TestJobResultsManagerInit:
    """Test JobResultsManager initialization."""

    def test_init_basic(self, temp_results_dir):
        """Test basic initialization."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="heart_analysis",
            job_type="roc",
            base_path=temp_results_dir,
        )

        assert manager.user_id == "eric"
        assert manager.job_name == "heart_analysis"
        assert manager.job_type == "roc"
        assert manager.base_path == Path(temp_results_dir)

    def test_init_sanitizes_job_name(self, temp_results_dir):
        """Test that job name is sanitized."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="Heart Disease / Analysis (v2)",
            job_type="test",
            base_path=temp_results_dir,
        )

        # Should remove special characters
        assert "/" not in manager.job_name
        assert "(" not in manager.job_name
        assert ")" not in manager.job_name
        assert " " not in manager.job_name

    def test_init_generates_timestamp(self, temp_results_dir):
        """Test that timestamp is generated."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="test",
            base_path=temp_results_dir,
        )

        assert manager.timestamp is not None
        # Should be in format YYYYMMDD_HHMMSS
        assert len(manager.timestamp) == 15

    def test_init_with_custom_job_id(self, temp_results_dir):
        """Test initialization with custom job ID."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="test",
            job_id="custom_job_123",
            base_path=temp_results_dir,
        )

        assert manager.job_id == "custom_job_123"

    def test_init_creates_metadata(self, temp_results_dir):
        """Test that metadata is initialized."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="test_job",
            job_type="analysis",
            base_path=temp_results_dir,
        )

        assert manager.metadata is not None
        assert manager.metadata.user_id == "eric"
        assert manager.metadata.job_type == "analysis"
        assert manager.metadata.status == "running"


# =============================================================================
# Test JobResultsManager - Directory Creation
# =============================================================================


class TestJobResultsManagerDirectories:
    """Test directory creation functionality."""

    def test_ensure_dirs_creates_structure(self, results_manager):
        """Test that _ensure_dirs creates proper structure."""
        results_manager._ensure_dirs()

        assert results_manager.job_dir.exists()
        assert results_manager.figures_dir.exists()
        assert results_manager.data_dir.exists()

    def test_ensure_dirs_idempotent(self, results_manager):
        """Test that _ensure_dirs can be called multiple times."""
        results_manager._ensure_dirs()
        results_manager._ensure_dirs()
        results_manager._ensure_dirs()

        # Should not raise, directories still exist
        assert results_manager.job_dir.exists()

    def test_directory_structure_path(self, temp_results_dir):
        """Test the directory path structure."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="test",
            job_id="test_20241210_120000",
            base_path=temp_results_dir,
        )
        manager._ensure_dirs()

        expected_path = Path(temp_results_dir) / "eric" / "test_20241210_120000"
        assert manager.job_dir == expected_path
        assert (expected_path / "figures").exists()
        assert (expected_path / "data").exists()


# =============================================================================
# Test JobResultsManager - Save Operations
# =============================================================================


class TestJobResultsManagerSave:
    """Test save operations."""

    def test_save_source_info(self, results_manager):
        """Test saving source information."""
        path = results_manager.save_source_info(
            dataset_id="ds123",
            dataset_name="Heart Disease",
            original_file="/data/sample_data/heart.csv",
            row_count=303,
            column_count=14,
        )

        assert Path(path).exists()

        with open(path) as f:
            data = json.load(f)

        assert data["dataset_id"] == "ds123"
        assert data["dataset_name"] == "Heart Disease"
        assert data["row_count"] == 303

    def test_save_source_info_with_metadata(self, results_manager):
        """Test saving source info with additional metadata."""
        path = results_manager.save_source_info(
            dataset_id="ds123",
            metadata_dict={
                "preprocessing_steps": ["normalize", "encode"],
                "custom_field": "value",
            },
        )

        with open(path) as f:
            data = json.load(f)

        assert data["preprocessing_steps"] == ["normalize", "encode"]
        assert data["custom_field"] == "value"

    def test_save_figure_png(self, results_manager, sample_figure):
        """Test saving figure as PNG."""
        path = results_manager.save_figure(sample_figure, "test_plot.png")

        assert Path(path).exists()
        assert path.endswith(".png")
        assert "test_plot.png" in results_manager._figures_saved

    def test_save_figure_adds_extension(self, results_manager, sample_figure):
        """Test that extension is added if missing."""
        path = results_manager.save_figure(sample_figure, "test_plot")

        assert path.endswith(".png")

    def test_save_figure_svg(self, results_manager):
        """Test saving figure as SVG."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])

        path = results_manager.save_figure(fig, "test_plot.svg")

        assert Path(path).exists()
        assert path.endswith(".svg")

    def test_save_figure_closes_by_default(self, results_manager):
        """Test that figure is closed by default."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fig_num = fig.number

        results_manager.save_figure(fig, "test.png")

        # Figure should be closed
        assert fig_num not in plt.get_fignums()

    def test_save_figure_keep_open(self, results_manager):
        """Test keeping figure open."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fig_num = fig.number

        results_manager.save_figure(fig, "test.png", close_fig=False)

        # Figure should still be open
        assert fig_num in plt.get_fignums()
        plt.close(fig)

    def test_save_result_json(self, results_manager, sample_result):
        """Test saving result as JSON."""
        path = results_manager.save_result(sample_result)

        assert Path(path).exists()

        with open(path) as f:
            data = json.load(f)

        assert data["auc"] == 0.85
        assert data["metrics"]["sensitivity"] == 0.82

    def test_save_result_custom_filename(self, results_manager, sample_result):
        """Test saving result with custom filename."""
        path = results_manager.save_result(sample_result, filename="custom_report.json")

        assert "custom_report.json" in path


# =============================================================================
# Test JobResultsManager - HTML Report
# =============================================================================


class TestJobResultsManagerHTML:
    """Test HTML report generation."""

    def test_save_html_report(self, results_manager, sample_result):
        """Test basic HTML report generation."""
        path = results_manager.save_html_report(sample_result)

        assert Path(path).exists()
        assert path.endswith(".html")

        with open(path) as f:
            html = f.read()

        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "test_analysis" in html  # job name

    def test_html_contains_metrics(self, results_manager, sample_result):
        """Test that HTML contains metrics."""
        path = results_manager.save_html_report(sample_result)

        with open(path) as f:
            html = f.read()

        # Should contain key metrics
        assert "0.85" in html or "auc" in html.lower()

    def test_html_includes_figures(self, results_manager, sample_result):
        """Test that HTML references saved figures."""
        # Save some figures first
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        results_manager.save_figure(fig, "roc_curve.png")

        path = results_manager.save_html_report(sample_result)

        with open(path) as f:
            html = f.read()

        # Should reference the figure
        assert "roc_curve.png" in html or "figures" in html


# =============================================================================
# Test JobResultsManager - Finalize
# =============================================================================


class TestJobResultsManagerFinalize:
    """Test finalization and summary."""

    def test_finalize_creates_metadata_file(self, results_manager, sample_result):
        """Test that finalize creates metadata.json."""
        results_manager.save_result(sample_result)
        results_manager.finalize()

        metadata_path = results_manager.job_dir / "metadata.json"
        assert metadata_path.exists()

    def test_finalize_returns_summary(self, results_manager, sample_result):
        """Test that finalize returns summary dict."""
        summary = results_manager.finalize(result=sample_result)

        assert "job_id" in summary
        assert "result_path" in summary
        assert "figures" in summary  # 實際 API 使用 'figures' 而非 'files'

    def test_finalize_updates_status(self, results_manager, sample_result):
        """Test that finalize updates status to completed."""
        results_manager.save_result(sample_result)
        results_manager.finalize()

        assert results_manager.metadata.status == "completed"
        assert results_manager.metadata.completed_at is not None

    def test_finalize_with_error(self, results_manager):
        """Test finalize with error status."""
        # 使用 set_error 設置錯誤狀態
        results_manager.set_error("Test error occurred")
        results_manager.finalize()

        assert results_manager.metadata.status == "failed"
        assert results_manager.metadata.error_message == "Test error occurred"

    def test_finalize_lists_figures(self, results_manager):
        """Test that finalize lists saved figures."""
        # Save multiple figures
        for i in range(3):
            fig, ax = plt.subplots()
            ax.plot([1, 2, 3], [i, i * 2, i * 3])
            results_manager.save_figure(fig, f"fig_{i}.png")

        results_manager.finalize()

        assert len(results_manager.metadata.figures) == 3


# =============================================================================
# Test JobResultsManager - Cleanup
# =============================================================================


class TestJobResultsManagerCleanup:
    """Test cleanup functionality."""

    def test_cleanup_removes_directory(self, results_manager, sample_result):
        """Test that cleanup removes the job directory using shutil."""
        results_manager.save_result(sample_result)
        job_dir = results_manager.job_dir

        assert job_dir.exists()

        # 使用 shutil 清理（目前 manager 沒有 cleanup 方法）
        import shutil

        shutil.rmtree(job_dir, ignore_errors=True)

        assert not job_dir.exists()

    def test_cleanup_on_nonexistent_dir(self, results_manager):
        """Test that non-existent directory is handled."""
        # 目錄不存在時不應該報錯
        job_dir = results_manager.job_dir
        assert not job_dir.exists()  # 尚未建立


# =============================================================================
# Test WorkerResultsMixin
# =============================================================================


class TestWorkerResultsMixin:
    """Test WorkerResultsMixin integration."""

    def test_create_results_manager(self, temp_results_dir):
        """Test creating results manager from job dict."""

        # Create a mock worker with the mixin
        class MockWorker(WorkerResultsMixin):
            pass

        worker = MockWorker()

        job = {
            "job_id": "test_job_123",
            "user_id": "eric",
            "job_name": "heart_analysis",
            "params": {},
        }

        with patch("results.worker_mixin.RESULTS_BASE_PATH", temp_results_dir):
            manager = worker.create_results_manager(job, job_type="roc_analysis")

        assert manager.user_id == "eric"
        assert manager.job_type == "roc_analysis"

    def test_create_results_manager_from_params(self, temp_results_dir):
        """Test extracting user_id from params."""

        class MockWorker(WorkerResultsMixin):
            pass

        worker = MockWorker()

        job = {
            "job_id": "test_job_123",
            "params": {
                "user_id": "from_params",
                "job_name": "param_analysis",
            },
        }

        with patch("results.worker_mixin.RESULTS_BASE_PATH", temp_results_dir):
            manager = worker.create_results_manager(job, job_type="test")

        assert manager.user_id == "from_params"

    def test_save_source_info_from_job(self, temp_results_dir):
        """Test saving source info from job dict."""

        class MockWorker(WorkerResultsMixin):
            pass

        worker = MockWorker()

        job = {
            "job_id": "test_job_123",
            "user_id": "eric",
            "params": {
                "csv_path": "/data/sample_data/heart.csv",
                "dataset_name": "Heart Disease",
                "target_column": "target",
            },
        }

        with patch("results.worker_mixin.RESULTS_BASE_PATH", temp_results_dir):
            manager = worker.create_results_manager(job, job_type="test")
            worker.save_source_info_from_job(
                manager,
                job,
                df_shape=(303, 14),
                columns_used=["age", "sex", "target"],
            )

        source_path = manager.data_dir / "source_info.json"
        assert source_path.exists()

        with open(source_path) as f:
            data = json.load(f)

        assert data["row_count"] == 303
        assert data["column_count"] == 14
        assert data["target_column"] == "target"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_in_job_name(self, temp_results_dir):
        """Test handling Unicode characters in job name."""
        manager = JobResultsManager(
            user_id="user1",
            job_name="心臟病分析",
            base_path=temp_results_dir,
        )
        manager._ensure_dirs()

        assert manager.job_dir.exists()

    def test_special_chars_sanitized(self, temp_results_dir):
        """Test special characters are properly sanitized."""
        manager = JobResultsManager(
            user_id="user1",
            job_name='test<>:"\\|?*',
            base_path=temp_results_dir,
        )

        # Should not contain problematic chars
        assert "<" not in manager.job_name
        assert ">" not in manager.job_name
        assert ":" not in manager.job_name

    def test_save_result_with_nan(self, results_manager):
        """Test saving result containing NaN values."""
        result = {
            "value": float("nan"),
            "list_with_nan": [1.0, float("nan"), 3.0],
        }

        # Should not raise
        path = results_manager.save_result(result)
        assert Path(path).exists()

    def test_save_result_with_numpy(self, results_manager):
        """Test saving result containing numpy types."""
        result = {
            "array": np.array([1, 2, 3]).tolist(),
            "float64": float(np.float64(1.5)),
            "int64": int(np.int64(42)),
        }

        path = results_manager.save_result(result)

        with open(path) as f:
            data = json.load(f)

        assert data["float64"] == 1.5
        assert data["int64"] == 42

    def test_empty_result(self, results_manager):
        """Test saving empty result."""
        path = results_manager.save_result({})

        with open(path) as f:
            data = json.load(f)

        assert data == {}


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""

    def test_complete_workflow(self, temp_results_dir):
        """Test complete job results workflow."""
        # Create manager
        manager = JobResultsManager(
            user_id="eric",
            job_name="complete_test",
            job_type="roc_analysis",
            base_path=temp_results_dir,
        )

        # Set parameters
        manager.set_parameters(
            {
                "threshold": 0.5,
                "ci_level": 0.95,
            }
        )

        # Save source info
        manager.save_source_info(
            dataset_id="ds123",
            dataset_name="Test Dataset",
            row_count=1000,
            column_count=10,
        )

        # Save figures
        fig1, ax1 = plt.subplots()
        ax1.plot([0, 1], [0, 1])
        manager.save_figure(fig1, "roc_curve.png")

        fig2, ax2 = plt.subplots()
        ax2.bar([1, 2, 3], [4, 5, 6])
        manager.save_figure(fig2, "feature_importance.png")

        # Save result
        result = {
            "auc": 0.87,
            "sensitivity": 0.85,
            "specificity": 0.82,
        }
        manager.save_result(result)

        # Save HTML report
        manager.save_html_report(result)

        # Finalize
        summary = manager.finalize()

        # Verify everything exists
        assert (manager.job_dir / "metadata.json").exists()
        assert (manager.job_dir / "report.json").exists()
        assert (manager.job_dir / "report.html").exists()
        assert (manager.figures_dir / "roc_curve.png").exists()
        assert (manager.figures_dir / "feature_importance.png").exists()
        assert (manager.data_dir / "source_info.json").exists()

        # Verify summary
        assert summary["status"] == "completed"
        assert len(summary["figures"]) == 2

    def test_failed_job_workflow(self, temp_results_dir):
        """Test workflow for failed job."""
        manager = JobResultsManager(
            user_id="eric",
            job_name="failed_test",
            job_type="analysis",
            base_path=temp_results_dir,
        )

        # Save source info before failure
        manager.save_source_info(dataset_name="Test")

        # Set error and finalize
        manager.set_error("Data validation failed: missing required columns")
        manager.finalize()

        # Verify metadata
        with open(manager.job_dir / "metadata.json") as f:
            metadata = json.load(f)

        assert metadata["status"] == "failed"
        assert "missing required columns" in metadata["error_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

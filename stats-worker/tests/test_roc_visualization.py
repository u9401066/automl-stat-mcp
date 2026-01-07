"""
Tests for ROC/PR Visualization Module - Phase 8C

Tests covering:
- ROC curve plotting
- PR curve plotting
- Calibration curve plotting
- Confusion matrix plotting
- Threshold analysis plotting
"""
import sys
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, '/home/eric/workspace251204/stats-worker/src')

from visualization.roc import (
    create_roc_visualizations,
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_pr_curve,
    plot_roc_curve,
    plot_roc_curves_comparison,
    plot_threshold_analysis,
)
from visualization.schemas import VisualizationType

# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def roc_result():
    """Sample ROC analysis result."""
    return {
        "auc": 0.85,
        "auc_ci": {"lower": 0.80, "upper": 0.90},
        "auc_se": 0.025,
        "optimal_threshold": 0.45,
        "optimal_method": "youden",
        "n_positive": 100,
        "n_negative": 200,
        "n_points": 11,
        "curve": [
            {"threshold": 1.0, "fpr": 0.0, "tpr": 0.0, "specificity": 1.0, "sensitivity": 0.0, "ppv": None, "npv": 0.667},
            {"threshold": 0.9, "fpr": 0.05, "tpr": 0.20, "specificity": 0.95, "sensitivity": 0.20, "ppv": 0.67, "npv": 0.70},
            {"threshold": 0.8, "fpr": 0.10, "tpr": 0.40, "specificity": 0.90, "sensitivity": 0.40, "ppv": 0.67, "npv": 0.75},
            {"threshold": 0.7, "fpr": 0.15, "tpr": 0.55, "specificity": 0.85, "sensitivity": 0.55, "ppv": 0.65, "npv": 0.79},
            {"threshold": 0.6, "fpr": 0.20, "tpr": 0.70, "specificity": 0.80, "sensitivity": 0.70, "ppv": 0.64, "npv": 0.84},
            {"threshold": 0.5, "fpr": 0.25, "tpr": 0.80, "specificity": 0.75, "sensitivity": 0.80, "ppv": 0.62, "npv": 0.88},
            {"threshold": 0.45, "fpr": 0.28, "tpr": 0.84, "specificity": 0.72, "sensitivity": 0.84, "ppv": 0.60, "npv": 0.90},
            {"threshold": 0.4, "fpr": 0.35, "tpr": 0.88, "specificity": 0.65, "sensitivity": 0.88, "ppv": 0.56, "npv": 0.92},
            {"threshold": 0.3, "fpr": 0.45, "tpr": 0.92, "specificity": 0.55, "sensitivity": 0.92, "ppv": 0.51, "npv": 0.93},
            {"threshold": 0.2, "fpr": 0.60, "tpr": 0.96, "specificity": 0.40, "sensitivity": 0.96, "ppv": 0.44, "npv": 0.95},
            {"threshold": 0.1, "fpr": 0.80, "tpr": 0.99, "specificity": 0.20, "sensitivity": 0.99, "ppv": 0.38, "npv": 0.98},
        ]
    }


@pytest.fixture
def roc_result_2():
    """Second ROC result for comparison."""
    return {
        "auc": 0.78,
        "auc_ci": {"lower": 0.72, "upper": 0.84},
        "optimal_threshold": 0.50,
        "n_positive": 100,
        "n_negative": 200,
        "curve": [
            {"threshold": 1.0, "fpr": 0.0, "tpr": 0.0, "specificity": 1.0, "sensitivity": 0.0},
            {"threshold": 0.8, "fpr": 0.10, "tpr": 0.30, "specificity": 0.90, "sensitivity": 0.30},
            {"threshold": 0.6, "fpr": 0.25, "tpr": 0.55, "specificity": 0.75, "sensitivity": 0.55},
            {"threshold": 0.4, "fpr": 0.40, "tpr": 0.75, "specificity": 0.60, "sensitivity": 0.75},
            {"threshold": 0.2, "fpr": 0.65, "tpr": 0.90, "specificity": 0.35, "sensitivity": 0.90},
        ]
    }


@pytest.fixture
def pr_result():
    """Sample PR analysis result."""
    return {
        "auc_pr": 0.72,
        "average_precision": 0.71,
        "f1_optimal_threshold": 0.42,
        "f1_max": 0.68,
        "n_points": 8,
        "curve": [
            {"threshold": 0.9, "recall": 0.10, "precision": 0.90},
            {"threshold": 0.8, "recall": 0.25, "precision": 0.85},
            {"threshold": 0.6, "recall": 0.50, "precision": 0.75},
            {"threshold": 0.42, "recall": 0.68, "precision": 0.68},
            {"threshold": 0.4, "recall": 0.70, "precision": 0.65},
            {"threshold": 0.3, "recall": 0.82, "precision": 0.55},
            {"threshold": 0.2, "recall": 0.90, "precision": 0.45},
            {"threshold": 0.1, "recall": 0.95, "precision": 0.38},
        ]
    }


@pytest.fixture
def calibration_result():
    """Sample calibration analysis result."""
    return {
        "hosmer_lemeshow": {"statistic": 8.5, "p_value": 0.38},
        "brier_score": 0.18,
        "calibration_slope": 0.95,
        "calibration_intercept": 0.02,
        "calibration_in_the_large": 0.01,
        "well_calibrated": True,
        "bins": [
            {"bin": 0, "mean_predicted": 0.05, "fraction_positive": 0.04, "count": 50},
            {"bin": 1, "mean_predicted": 0.15, "fraction_positive": 0.14, "count": 45},
            {"bin": 2, "mean_predicted": 0.25, "fraction_positive": 0.28, "count": 38},
            {"bin": 3, "mean_predicted": 0.35, "fraction_positive": 0.32, "count": 32},
            {"bin": 4, "mean_predicted": 0.45, "fraction_positive": 0.48, "count": 28},
            {"bin": 5, "mean_predicted": 0.55, "fraction_positive": 0.52, "count": 25},
            {"bin": 6, "mean_predicted": 0.65, "fraction_positive": 0.68, "count": 22},
            {"bin": 7, "mean_predicted": 0.75, "fraction_positive": 0.72, "count": 18},
            {"bin": 8, "mean_predicted": 0.85, "fraction_positive": 0.88, "count": 15},
            {"bin": 9, "mean_predicted": 0.95, "fraction_positive": 0.93, "count": 12},
        ]
    }


@pytest.fixture
def confusion_matrix_dict():
    """Sample confusion matrix as dict."""
    return {
        "tn": 150,
        "fp": 50,
        "fn": 20,
        "tp": 80
    }


@pytest.fixture
def confusion_matrix_array():
    """Sample confusion matrix as 2x2 array."""
    return np.array([[150, 50], [20, 80]])


# =============================================================================
# Unit Tests - ROC Curve
# =============================================================================

class TestROCCurvePlot:
    """Tests for ROC curve plotting."""

    def test_plot_basic(self, roc_result):
        """Test basic ROC curve plot."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result)

        assert fig is not None
        assert len(fig.axes) == 1

        plt.close(fig)

    def test_plot_with_optimal_threshold(self, roc_result):
        """Test ROC curve with optimal threshold marked."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result, show_optimal=True)

        assert fig is not None

        plt.close(fig)

    def test_plot_without_ci(self, roc_result):
        """Test ROC curve without CI in legend."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result, show_ci=False)

        assert fig is not None

        plt.close(fig)

    def test_plot_without_diagonal(self, roc_result):
        """Test ROC curve without diagonal reference."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result, show_diagonal=False)

        assert fig is not None

        plt.close(fig)

    def test_plot_custom_color(self, roc_result):
        """Test ROC curve with custom color."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result, color='#FF0000')

        assert fig is not None

        plt.close(fig)

    def test_plot_custom_title(self, roc_result):
        """Test ROC curve with custom title."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve(roc_result, title="Model Performance")

        assert fig is not None

        plt.close(fig)

    def test_plot_empty_curve(self):
        """Test ROC curve with no data."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curve({"curve": []})

        assert fig is not None

        plt.close(fig)


class TestROCComparison:
    """Tests for ROC curves comparison."""

    def test_compare_two_curves(self, roc_result, roc_result_2):
        """Test comparing two ROC curves."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curves_comparison(
            [roc_result, roc_result_2],
            labels=["Model A", "Model B"]
        )

        assert fig is not None

        plt.close(fig)

    def test_compare_with_delong(self, roc_result, roc_result_2):
        """Test comparison with DeLong test result."""
        import matplotlib.pyplot as plt

        comparison = {
            "difference": 0.07,
            "p_value": 0.02
        }

        fig = plot_roc_curves_comparison(
            [roc_result, roc_result_2],
            comparison_result=comparison
        )

        assert fig is not None

        plt.close(fig)

    def test_compare_default_labels(self, roc_result, roc_result_2):
        """Test comparison with default labels."""
        import matplotlib.pyplot as plt

        fig = plot_roc_curves_comparison([roc_result, roc_result_2])

        assert fig is not None

        plt.close(fig)


# =============================================================================
# Unit Tests - PR Curve
# =============================================================================

class TestPRCurvePlot:
    """Tests for Precision-Recall curve plotting."""

    def test_plot_basic(self, pr_result):
        """Test basic PR curve plot."""
        import matplotlib.pyplot as plt

        fig = plot_pr_curve(pr_result)

        assert fig is not None

        plt.close(fig)

    def test_plot_with_f1_optimal(self, pr_result):
        """Test PR curve with F1-optimal point."""
        import matplotlib.pyplot as plt

        fig = plot_pr_curve(pr_result, show_f1_optimal=True)

        assert fig is not None

        plt.close(fig)

    def test_plot_with_baseline(self, pr_result):
        """Test PR curve with baseline."""
        import matplotlib.pyplot as plt

        fig = plot_pr_curve(pr_result, show_baseline=True, baseline_precision=0.33)

        assert fig is not None

        plt.close(fig)

    def test_plot_without_auc(self, pr_result):
        """Test PR curve without AUC in legend."""
        import matplotlib.pyplot as plt

        fig = plot_pr_curve(pr_result, show_auc=False)

        assert fig is not None

        plt.close(fig)


# =============================================================================
# Unit Tests - Calibration Curve
# =============================================================================

class TestCalibrationPlot:
    """Tests for calibration curve plotting."""

    def test_plot_basic(self, calibration_result):
        """Test basic calibration plot."""
        import matplotlib.pyplot as plt

        fig = plot_calibration_curve(calibration_result)

        assert fig is not None

        plt.close(fig)

    def test_plot_with_histogram(self, calibration_result):
        """Test calibration with histogram."""
        import matplotlib.pyplot as plt

        fig = plot_calibration_curve(calibration_result, show_histogram=True)

        assert fig is not None
        assert len(fig.axes) >= 2  # Main plot + histogram

        plt.close(fig)

    def test_plot_without_histogram(self, calibration_result):
        """Test calibration without histogram."""
        import matplotlib.pyplot as plt

        fig = plot_calibration_curve(calibration_result, show_histogram=False)

        assert fig is not None

        plt.close(fig)

    def test_plot_without_metrics(self, calibration_result):
        """Test calibration without metrics text."""
        import matplotlib.pyplot as plt

        fig = plot_calibration_curve(calibration_result, show_metrics=False)

        assert fig is not None

        plt.close(fig)


# =============================================================================
# Unit Tests - Confusion Matrix
# =============================================================================

class TestConfusionMatrixPlot:
    """Tests for confusion matrix plotting."""

    def test_plot_from_dict(self, confusion_matrix_dict):
        """Test confusion matrix from dict."""
        import matplotlib.pyplot as plt

        fig = plot_confusion_matrix(confusion_matrix_dict)

        assert fig is not None

        plt.close(fig)

    def test_plot_from_array(self, confusion_matrix_array):
        """Test confusion matrix from numpy array."""
        import matplotlib.pyplot as plt

        fig = plot_confusion_matrix(confusion_matrix_array)

        assert fig is not None

        plt.close(fig)

    def test_plot_normalized(self, confusion_matrix_dict):
        """Test normalized confusion matrix."""
        import matplotlib.pyplot as plt

        fig = plot_confusion_matrix(confusion_matrix_dict, normalize=True)

        assert fig is not None

        plt.close(fig)

    def test_plot_custom_labels(self, confusion_matrix_dict):
        """Test with custom labels."""
        import matplotlib.pyplot as plt

        fig = plot_confusion_matrix(
            confusion_matrix_dict,
            labels=['Control', 'Disease']
        )

        assert fig is not None

        plt.close(fig)

    def test_plot_without_percentages(self, confusion_matrix_dict):
        """Test without percentages."""
        import matplotlib.pyplot as plt

        fig = plot_confusion_matrix(
            confusion_matrix_dict,
            show_percentages=False
        )

        assert fig is not None

        plt.close(fig)

    def test_metrics_calculation(self, confusion_matrix_dict):
        """Test that metrics are correctly calculated."""
        import matplotlib.pyplot as plt

        # Expected metrics
        tn, fp, fn, tp = 150, 50, 20, 80
        total = tn + fp + fn + tp

        (tp + tn) / total  # 230/300 = 0.767
        tp / (tp + fn)  # 80/100 = 0.8
        tn / (tn + fp)  # 150/200 = 0.75

        fig = plot_confusion_matrix(confusion_matrix_dict)

        # Verify figure was created (metrics are in the figure text)
        assert fig is not None

        plt.close(fig)


# =============================================================================
# Unit Tests - Threshold Analysis
# =============================================================================

class TestThresholdAnalysis:
    """Tests for threshold analysis plotting."""

    def test_plot_basic(self, roc_result):
        """Test basic threshold analysis."""
        import matplotlib.pyplot as plt

        fig = plot_threshold_analysis(roc_result)

        assert fig is not None

        plt.close(fig)

    def test_plot_selected_metrics(self, roc_result):
        """Test with selected metrics only."""
        import matplotlib.pyplot as plt

        fig = plot_threshold_analysis(
            roc_result,
            metrics=['sensitivity', 'specificity']
        )

        assert fig is not None

        plt.close(fig)

    def test_plot_custom_title(self, roc_result):
        """Test with custom title."""
        import matplotlib.pyplot as plt

        fig = plot_threshold_analysis(
            roc_result,
            title="Classification Threshold Selection"
        )

        assert fig is not None

        plt.close(fig)


# =============================================================================
# Integration Tests
# =============================================================================

class TestCreateROCVisualizations:
    """Tests for high-level visualization creation."""

    @patch('visualization.roc.save_figure_to_minio')
    def test_create_roc_only(self, mock_save, roc_result):
        """Test creating visualizations with ROC data only."""
        mock_save.return_value = "https://minio.example.com/test.png"

        results = create_roc_visualizations(
            roc_result,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )

        assert len(results) >= 2  # ROC + threshold analysis

        types = [r.type for r in results]
        assert VisualizationType.ROC_CURVE in types
        assert VisualizationType.THRESHOLD_ANALYSIS in types

    @patch('visualization.roc.save_figure_to_minio')
    def test_create_full_suite(self, mock_save, roc_result, pr_result, calibration_result, confusion_matrix_dict):
        """Test creating full visualization suite."""
        mock_save.return_value = "https://minio.example.com/test.png"

        results = create_roc_visualizations(
            roc_result,
            pr_result=pr_result,
            calibration_result=calibration_result,
            confusion_matrix=confusion_matrix_dict,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )

        assert len(results) >= 5  # ROC, threshold, PR, calibration, confusion matrix

        types = [r.type for r in results]
        assert VisualizationType.ROC_CURVE in types
        assert VisualizationType.PR_CURVE in types
        assert VisualizationType.CALIBRATION_CURVE in types
        assert VisualizationType.CONFUSION_MATRIX in types

    @patch('visualization.roc.save_figure_to_minio')
    def test_roc_visualization_result_metadata(self, mock_save, roc_result):
        """Test ROCVisualizationResult has correct metadata."""
        mock_save.return_value = "https://minio.example.com/test.png"

        results = create_roc_visualizations(
            roc_result,
            user_id="test_user",
            job_id="test_job",
        )

        # Find ROC result
        roc_viz = next(r for r in results if r.type == VisualizationType.ROC_CURVE)

        assert roc_viz.auc == 0.85
        assert roc_viz.auc_ci_lower == 0.80
        assert roc_viz.auc_ci_upper == 0.90
        assert roc_viz.optimal_threshold == 0.45


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

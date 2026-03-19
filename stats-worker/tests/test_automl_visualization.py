"""
Tests for AutoML Visualization Module

Tests feature importance, SHAP, learning curves, and model comparison plots.
"""

import sys
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/home/eric/workspace251204/stats-worker/src")

from visualization.automl import (
    AUTOML_COLORS,
    MODEL_TYPE_COLORS,
    _get_model_color,
    create_automl_visualizations,
    plot_algorithm_performance,
    plot_feature_importance,
    plot_learning_curve,
    plot_model_comparison,
    plot_prediction_vs_actual,
    plot_residuals,
    plot_shap_summary,
    plot_shap_waterfall,
)
from visualization.schemas import VisualizationType

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_feature_importance():
    """Sample feature importance dictionary."""
    return {
        "age": 0.25,
        "income": 0.20,
        "education": 0.15,
        "gender": 0.10,
        "experience": 0.08,
        "location": 0.07,
        "marital_status": 0.05,
        "hours_per_week": 0.04,
        "occupation": 0.03,
        "native_country": 0.03,
    }


@pytest.fixture
def sample_leaderboard():
    """Sample AutoML leaderboard."""
    return [
        {"model_name": "WeightedEnsemble_L2", "score": 0.92, "fit_time": 120.5, "pred_time": 0.5},
        {"model_name": "LightGBM", "score": 0.90, "fit_time": 45.2, "pred_time": 0.1},
        {"model_name": "XGBoost", "score": 0.89, "fit_time": 60.3, "pred_time": 0.15},
        {"model_name": "CatBoost", "score": 0.88, "fit_time": 80.1, "pred_time": 0.2},
        {"model_name": "RandomForest", "score": 0.86, "fit_time": 30.0, "pred_time": 0.3},
        {"model_name": "NeuralNetTorch", "score": 0.85, "fit_time": 200.0, "pred_time": 0.05},
    ]


@pytest.fixture
def sample_shap_values():
    """Sample SHAP values array."""
    np.random.seed(42)
    n_samples = 100
    n_features = 10
    return np.random.randn(n_samples, n_features) * 0.5


@pytest.fixture
def sample_features():
    """Sample feature DataFrame for SHAP plots."""
    np.random.seed(42)
    n_samples = 100
    return pd.DataFrame(
        {
            "age": np.random.randint(18, 80, n_samples),
            "income": np.random.uniform(20000, 150000, n_samples),
            "education": np.random.randint(8, 20, n_samples),
            "gender": np.random.choice([0, 1], n_samples),
            "experience": np.random.randint(0, 40, n_samples),
            "location": np.random.randint(1, 50, n_samples),
            "marital_status": np.random.choice([0, 1, 2], n_samples),
            "hours_per_week": np.random.randint(20, 80, n_samples),
            "occupation": np.random.randint(1, 15, n_samples),
            "native_country": np.random.randint(1, 40, n_samples),
        }
    )


@pytest.fixture
def sample_learning_curve_data():
    """Sample learning curve data."""
    train_sizes = np.array([100, 200, 400, 800, 1600])
    train_scores = np.array([0.98, 0.95, 0.92, 0.90, 0.88])
    val_scores = np.array([0.75, 0.80, 0.84, 0.86, 0.87])
    train_std = np.array([0.02, 0.02, 0.01, 0.01, 0.01])
    val_std = np.array([0.05, 0.04, 0.03, 0.02, 0.02])
    return train_sizes, train_scores, val_scores, train_std, val_std


@pytest.fixture
def sample_regression_data():
    """Sample regression predictions."""
    np.random.seed(42)
    n_samples = 100
    y_true = np.random.uniform(10, 100, n_samples)
    noise = np.random.normal(0, 5, n_samples)
    y_pred = y_true + noise
    return y_true, y_pred


# =============================================================================
# Test Feature Importance Plot
# =============================================================================


class TestPlotFeatureImportance:
    """Tests for plot_feature_importance."""

    def test_basic_horizontal_bar(self, sample_feature_importance):
        """Test basic horizontal bar chart."""
        fig = plot_feature_importance(sample_feature_importance)

        assert isinstance(fig, plt.Figure)
        ax = fig.axes[0]
        assert len(ax.patches) == len(sample_feature_importance)
        plt.close(fig)

    def test_vertical_bar(self, sample_feature_importance):
        """Test vertical bar chart."""
        fig = plot_feature_importance(sample_feature_importance, horizontal=False)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_top_n_features(self, sample_feature_importance):
        """Test limiting to top N features."""
        fig = plot_feature_importance(sample_feature_importance, top_n=5)

        ax = fig.axes[0]
        assert len(ax.patches) == 5
        plt.close(fig)

    def test_from_dataframe(self, sample_feature_importance):
        """Test with DataFrame input."""
        df = pd.DataFrame(list(sample_feature_importance.items()), columns=["feature", "importance"])
        fig = plot_feature_importance(df)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_from_series(self, sample_feature_importance):
        """Test with Series input."""
        series = pd.Series(sample_feature_importance)
        fig = plot_feature_importance(series)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_title_and_xlabel(self, sample_feature_importance):
        """Test custom title and labels."""
        fig = plot_feature_importance(sample_feature_importance, title="Custom Title", xlabel="Gini Importance")

        ax = fig.axes[0]
        assert ax.get_title() == "Custom Title"
        assert ax.get_xlabel() == "Gini Importance"
        plt.close(fig)

    def test_without_values(self, sample_feature_importance):
        """Test without showing values on bars."""
        fig = plot_feature_importance(sample_feature_importance, show_values=False)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_with_error_bars(self, sample_feature_importance):
        """Test with error bars."""
        error_bars = dict.fromkeys(sample_feature_importance.keys(), 0.01)
        fig = plot_feature_importance(sample_feature_importance, error_bars=error_bars)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# =============================================================================
# Test SHAP Plots
# =============================================================================


class TestPlotShapSummary:
    """Tests for plot_shap_summary."""

    def test_bar_plot_fallback(self, sample_shap_values, sample_features):
        """Test bar plot fallback when SHAP library not available."""
        fig = plot_shap_summary(sample_shap_values, sample_features, plot_type="bar", title="SHAP Summary")

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_with_feature_names(self, sample_shap_values, sample_features):
        """Test with explicit feature names."""
        feature_names = list(sample_features.columns)
        fig = plot_shap_summary(sample_shap_values, sample_features.values, feature_names=feature_names)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_max_display(self, sample_shap_values, sample_features):
        """Test max_display parameter."""
        fig = plot_shap_summary(sample_shap_values, sample_features, max_display=5)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestPlotShapWaterfall:
    """Tests for plot_shap_waterfall."""

    def test_basic_waterfall(self, sample_shap_values, sample_features):
        """Test basic waterfall plot."""
        fig = plot_shap_waterfall(sample_shap_values, sample_features, sample_idx=0)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_single_sample_shap(self, sample_features):
        """Test with single sample SHAP values."""
        single_shap = np.random.randn(10) * 0.5
        single_features = sample_features.iloc[0]

        fig = plot_shap_waterfall(single_shap, single_features, title="Single Prediction Explanation")

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_max_display(self, sample_shap_values, sample_features):
        """Test max_display parameter."""
        fig = plot_shap_waterfall(sample_shap_values, sample_features, sample_idx=0, max_display=5)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# =============================================================================
# Test Learning Curve Plot
# =============================================================================


class TestPlotLearningCurve:
    """Tests for plot_learning_curve."""

    def test_basic_learning_curve(self, sample_learning_curve_data):
        """Test basic learning curve."""
        train_sizes, train_scores, val_scores, _, _ = sample_learning_curve_data

        fig = plot_learning_curve(train_sizes, train_scores, val_scores)

        assert isinstance(fig, plt.Figure)
        ax = fig.axes[0]
        assert len(ax.lines) >= 2  # At least train and val lines
        plt.close(fig)

    def test_with_std(self, sample_learning_curve_data):
        """Test with standard deviation bands."""
        train_sizes, train_scores, val_scores, train_std, val_std = sample_learning_curve_data

        fig = plot_learning_curve(train_sizes, train_scores, val_scores, train_std=train_std, val_std=val_std)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_labels(self, sample_learning_curve_data):
        """Test with custom labels."""
        train_sizes, train_scores, val_scores, _, _ = sample_learning_curve_data

        fig = plot_learning_curve(
            train_sizes,
            train_scores,
            val_scores,
            title="Model Learning Curve",
            xlabel="Training Set Size",
            ylabel="Accuracy",
        )

        ax = fig.axes[0]
        assert ax.get_title() == "Model Learning Curve"
        assert ax.get_xlabel() == "Training Set Size"
        plt.close(fig)

    def test_overfitting_diagnosis(self):
        """Test overfitting diagnosis annotation."""
        train_sizes = np.array([100, 200, 400, 800])
        train_scores = np.array([0.99, 0.99, 0.98, 0.98])  # High train
        val_scores = np.array([0.70, 0.72, 0.73, 0.74])  # Low val

        fig = plot_learning_curve(train_sizes, train_scores, val_scores)

        # Check annotation text exists
        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert any("overfitting" in t.lower() for t in texts)
        plt.close(fig)


# =============================================================================
# Test Model Comparison Plot
# =============================================================================


class TestPlotModelComparison:
    """Tests for plot_model_comparison."""

    def test_basic_comparison(self, sample_leaderboard):
        """Test basic model comparison."""
        fig = plot_model_comparison(sample_leaderboard)

        assert isinstance(fig, plt.Figure)
        ax = fig.axes[0]
        assert len(ax.patches) == len(sample_leaderboard)
        plt.close(fig)

    def test_top_n_models(self, sample_leaderboard):
        """Test limiting to top N models."""
        fig = plot_model_comparison(sample_leaderboard, top_n=3)

        ax = fig.axes[0]
        assert len(ax.patches) == 3
        plt.close(fig)

    def test_from_dataframe(self, sample_leaderboard):
        """Test with DataFrame input."""
        df = pd.DataFrame(sample_leaderboard)
        fig = plot_model_comparison(df)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_without_time(self, sample_leaderboard):
        """Test without showing training time."""
        fig = plot_model_comparison(sample_leaderboard, show_time=False)

        assert isinstance(fig, plt.Figure)
        # Should only have one axes (no secondary axis)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_custom_metric_name(self, sample_leaderboard):
        """Test custom metric name."""
        fig = plot_model_comparison(sample_leaderboard, metric="score", metric_name="ROC AUC")

        ax = fig.axes[0]
        assert "ROC AUC" in ax.get_xlabel()
        plt.close(fig)

    def test_model_type_colors(self):
        """Test that models get appropriate colors."""
        assert _get_model_color("WeightedEnsemble_L2") == MODEL_TYPE_COLORS["WeightedEnsemble"]
        assert _get_model_color("LightGBM_1") == MODEL_TYPE_COLORS["LightGBM"]
        assert _get_model_color("XGBoost_BAG_L1") == MODEL_TYPE_COLORS["XGBoost"]
        assert _get_model_color("UnknownModel") == MODEL_TYPE_COLORS["default"]


class TestPlotAlgorithmPerformance:
    """Tests for plot_algorithm_performance."""

    def test_basic_algorithm_comparison(self):
        """Test basic algorithm performance comparison."""
        results = {
            "XGBoost": {"accuracy": 0.89, "f1": 0.87, "auc": 0.92},
            "LightGBM": {"accuracy": 0.90, "f1": 0.88, "auc": 0.93},
            "RandomForest": {"accuracy": 0.86, "f1": 0.84, "auc": 0.89},
        }

        fig = plot_algorithm_performance(results)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_metrics(self):
        """Test with custom metrics list."""
        results = {
            "Model_A": {"precision": 0.85, "recall": 0.80},
            "Model_B": {"precision": 0.82, "recall": 0.88},
        }

        fig = plot_algorithm_performance(results, metrics=["precision", "recall"])

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# =============================================================================
# Test Regression Plots
# =============================================================================


class TestPlotPredictionVsActual:
    """Tests for plot_prediction_vs_actual."""

    def test_basic_plot(self, sample_regression_data):
        """Test basic prediction vs actual plot."""
        y_true, y_pred = sample_regression_data

        fig = plot_prediction_vs_actual(y_true, y_pred)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_with_metrics(self, sample_regression_data):
        """Test that metrics are shown."""
        y_true, y_pred = sample_regression_data

        fig = plot_prediction_vs_actual(y_true, y_pred, show_metrics=True)

        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert any("R²" in t or "R2" in t.upper() for t in texts)
        plt.close(fig)

    def test_without_metrics(self, sample_regression_data):
        """Test without showing metrics."""
        y_true, y_pred = sample_regression_data

        fig = plot_prediction_vs_actual(y_true, y_pred, show_metrics=False)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestPlotResiduals:
    """Tests for plot_residuals."""

    def test_basic_residual_plot(self, sample_regression_data):
        """Test basic residual plot."""
        y_true, y_pred = sample_regression_data

        fig = plot_residuals(y_true, y_pred)

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2  # Scatter and histogram
        plt.close(fig)

    def test_residual_statistics(self, sample_regression_data):
        """Test residual statistics are shown."""
        y_true, y_pred = sample_regression_data

        fig = plot_residuals(y_true, y_pred)

        # Check histogram axis has statistics text
        ax_hist = fig.axes[1]
        texts = [t.get_text() for t in ax_hist.texts]
        assert any("Mean" in t for t in texts)
        plt.close(fig)


# =============================================================================
# Test High-Level Visualization Creator
# =============================================================================


class TestCreateAutomlVisualizations:
    """Tests for create_automl_visualizations."""

    @patch("visualization.automl.save_figure_to_minio")
    def test_with_feature_importance(self, mock_save, sample_feature_importance):
        """Test creating visualizations with feature importance."""
        mock_save.return_value = "http://minio/test.png"

        model_result = {"feature_importance": sample_feature_importance, "problem_type": "binary"}

        results = create_automl_visualizations(model_result, user_id="test_user", job_id="test_job", save_to_minio=True)

        assert len(results) >= 1
        assert any(r.type == VisualizationType.FEATURE_IMPORTANCE for r in results)
        plt.close("all")

    @patch("visualization.automl.save_figure_to_minio")
    def test_with_leaderboard(self, mock_save, sample_leaderboard):
        """Test creating visualizations with leaderboard."""
        mock_save.return_value = "http://minio/test.png"

        model_result = {"leaderboard": sample_leaderboard, "metric": "accuracy", "problem_type": "binary"}

        results = create_automl_visualizations(model_result, user_id="test_user", job_id="test_job", save_to_minio=True)

        assert len(results) >= 1
        assert any(r.type == VisualizationType.MODEL_COMPARISON for r in results)
        plt.close("all")

    @patch("visualization.automl.save_figure_to_minio")
    def test_with_shap_values(self, mock_save, sample_shap_values, sample_features):
        """Test creating visualizations with SHAP values."""
        mock_save.return_value = "http://minio/test.png"

        model_result = {"problem_type": "binary"}

        results = create_automl_visualizations(
            model_result,
            X=sample_features,
            shap_values=sample_shap_values,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )

        assert len(results) >= 1
        assert any(r.type == VisualizationType.SHAP_SUMMARY for r in results)
        plt.close("all")

    @patch("visualization.automl.save_figure_to_minio")
    def test_regression_plots(self, mock_save, sample_regression_data):
        """Test creating regression visualizations."""
        mock_save.return_value = "http://minio/test.png"

        y_true, y_pred = sample_regression_data

        model_result = {"problem_type": "regression"}

        results = create_automl_visualizations(
            model_result, y_true=y_true, y_pred=y_pred, user_id="test_user", job_id="test_job", save_to_minio=True
        )

        assert len(results) >= 2  # prediction_vs_actual and residuals
        plt.close("all")

    def test_without_minio(self, sample_feature_importance):
        """Test creating visualizations without saving to MinIO."""
        model_result = {"feature_importance": sample_feature_importance, "problem_type": "binary"}

        results = create_automl_visualizations(model_result, save_to_minio=False)

        assert len(results) >= 1
        assert results[0].url == ""  # No URL when not saving
        plt.close("all")

    def test_all_visualizations(
        self, sample_feature_importance, sample_leaderboard, sample_shap_values, sample_features, sample_regression_data
    ):
        """Test creating all visualization types."""
        y_true, y_pred = sample_regression_data

        model_result = {
            "feature_importance": sample_feature_importance,
            "leaderboard": sample_leaderboard,
            "problem_type": "regression",
            "metric": "rmse",
        }

        results = create_automl_visualizations(
            model_result,
            X=sample_features,
            y_true=y_true,
            y_pred=y_pred,
            shap_values=sample_shap_values,
            save_to_minio=False,
        )

        # Should have multiple visualizations
        assert len(results) >= 4

        # Check types
        types = [r.type for r in results]
        assert VisualizationType.FEATURE_IMPORTANCE in types
        assert VisualizationType.MODEL_COMPARISON in types
        assert VisualizationType.SHAP_SUMMARY in types

        plt.close("all")


# =============================================================================
# Test Color Constants
# =============================================================================


class TestColorConstants:
    """Tests for color constants."""

    def test_automl_colors(self):
        """Test AUTOML_COLORS dict."""
        assert "primary" in AUTOML_COLORS
        assert "secondary" in AUTOML_COLORS
        assert "positive" in AUTOML_COLORS
        assert "negative" in AUTOML_COLORS

    def test_model_type_colors(self):
        """Test MODEL_TYPE_COLORS dict."""
        assert "LightGBM" in MODEL_TYPE_COLORS
        assert "XGBoost" in MODEL_TYPE_COLORS
        assert "RandomForest" in MODEL_TYPE_COLORS
        assert "NeuralNet" in MODEL_TYPE_COLORS
        assert "default" in MODEL_TYPE_COLORS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

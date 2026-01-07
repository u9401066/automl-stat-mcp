"""
AutoML Visualization Module

Provides plotting functions for AutoML training results:
- Feature importance bar charts
- SHAP summary and waterfall plots
- Learning curves
- Model comparison leaderboards
- Calibration analysis

These plots are typically generated after AutoML training to explain
model behavior and compare algorithm performance.

Usage:
    from visualization.automl import plot_feature_importance, plot_shap_summary

    # Plot feature importance
    fig = plot_feature_importance(importance_dict)

    # Plot SHAP summary (requires SHAP values)
    fig = plot_shap_summary(shap_values, feature_names)
"""
import matplotlib

matplotlib.use('Agg')
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .schemas import (
    VisualizationResult,
    VisualizationType,
)
from .storage import save_figure_to_minio
from .style import (
    apply_publication_style,
)

logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    logger.debug("SHAP not available - SHAP plots will be disabled")


# =============================================================================
# Color Palettes
# =============================================================================

AUTOML_COLORS = {
    'primary': '#1f77b4',       # Blue
    'secondary': '#ff7f0e',     # Orange
    'positive': '#2ca02c',      # Green
    'negative': '#d62728',      # Red
    'neutral': '#7f7f7f',       # Gray
    'highlight': '#e377c2',     # Pink
    'ensemble': '#17becf',      # Cyan for ensemble models
    'neural': '#bcbd22',        # Yellow-green for neural nets
    'tree': '#8c564b',          # Brown for tree models
}

MODEL_TYPE_COLORS = {
    'WeightedEnsemble': AUTOML_COLORS['ensemble'],
    'LightGBM': AUTOML_COLORS['primary'],
    'XGBoost': AUTOML_COLORS['secondary'],
    'CatBoost': '#9467bd',      # Purple
    'RandomForest': AUTOML_COLORS['tree'],
    'ExtraTrees': '#8c564b',
    'NeuralNet': AUTOML_COLORS['neural'],
    'KNeighbors': '#17becf',
    'LinearModel': '#7f7f7f',
    'default': AUTOML_COLORS['neutral'],
}


def _get_model_color(model_name: str) -> str:
    """Get color for a model based on its type."""
    for key, color in MODEL_TYPE_COLORS.items():
        if key.lower() in model_name.lower():
            return color
    return MODEL_TYPE_COLORS['default']


# =============================================================================
# Feature Importance Plot
# =============================================================================

def plot_feature_importance(
    importance: Union[Dict[str, float], pd.DataFrame, pd.Series],
    top_n: int = 20,
    title: str = "Feature Importance",
    xlabel: str = "Importance",
    horizontal: bool = True,
    show_values: bool = True,
    figsize: Optional[Tuple[float, float]] = None,
    color: str = AUTOML_COLORS['primary'],
    error_bars: Optional[Dict[str, float]] = None,
) -> plt.Figure:
    """
    Plot feature importance as a bar chart.

    Supports various input formats and shows top N most important features.

    Args:
        importance: Feature importance as dict, DataFrame, or Series
            - Dict: {feature_name: importance_value}
            - DataFrame: columns=['feature', 'importance'] or index=features
            - Series: index=features, values=importance
        top_n: Number of top features to show
        title: Plot title
        xlabel: X-axis label
        horizontal: If True, horizontal bars; else vertical
        show_values: Show importance values on bars
        figsize: Figure size (auto-calculated if None)
        color: Bar color
        error_bars: Optional std dev for error bars {feature: std}

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    # Convert to DataFrame
    if isinstance(importance, dict):
        df = pd.DataFrame(list(importance.items()), columns=['feature', 'importance'])
    elif isinstance(importance, pd.Series):
        df = pd.DataFrame({'feature': importance.index, 'importance': importance.values})
    elif isinstance(importance, pd.DataFrame):
        if 'feature' not in importance.columns:
            # Assume index is features
            df = pd.DataFrame({'feature': importance.index, 'importance': importance.iloc[:, 0].values})
        else:
            df = importance.copy()
    else:
        raise ValueError(f"Unsupported importance type: {type(importance)}")

    # Sort and take top N
    df = df.sort_values('importance', ascending=False).head(top_n)

    # Determine figure size
    if figsize is None:
        if horizontal:
            figsize = (8, max(4, len(df) * 0.3))
        else:
            figsize = (max(6, len(df) * 0.5), 6)

    fig, ax = plt.subplots(figsize=figsize)

    if horizontal:
        # Horizontal bar chart (features on y-axis)
        df = df.sort_values('importance', ascending=True)  # Reverse for horizontal

        y_pos = np.arange(len(df))

        # Error bars if provided
        xerr = None
        if error_bars:
            xerr = [error_bars.get(f, 0) for f in df['feature']]

        bars = ax.barh(y_pos, df['importance'], xerr=xerr, color=color,
                       edgecolor='black', linewidth=0.5, capsize=3)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['feature'])
        ax.set_xlabel(xlabel)

        if show_values:
            for _i, (bar, val) in enumerate(zip(bars, df['importance'], strict=False)):
                ax.text(bar.get_width() + 0.01 * ax.get_xlim()[1], bar.get_y() + bar.get_height()/2,
                        f'{val:.3f}', va='center', fontsize=9)
    else:
        # Vertical bar chart
        x_pos = np.arange(len(df))

        yerr = None
        if error_bars:
            yerr = [error_bars.get(f, 0) for f in df['feature']]

        bars = ax.bar(x_pos, df['importance'], yerr=yerr, color=color,
                      edgecolor='black', linewidth=0.5, capsize=3)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(df['feature'], rotation=45, ha='right')
        ax.set_ylabel(xlabel)

        if show_values:
            for bar, val in zip(bars, df['importance'], strict=False):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01 * ax.get_ylim()[1],
                        f'{val:.3f}', ha='center', va='bottom', fontsize=8, rotation=90)

    ax.set_title(title)

    plt.tight_layout()

    return fig


# =============================================================================
# SHAP Summary Plot
# =============================================================================

def plot_shap_summary(
    shap_values: np.ndarray,
    features: Union[pd.DataFrame, np.ndarray],
    feature_names: Optional[List[str]] = None,
    max_display: int = 20,
    title: str = "SHAP Feature Importance",
    plot_type: str = "dot",  # "dot", "bar", "violin"
    figsize: Tuple[float, float] = (10, 8),
) -> plt.Figure:
    """
    Plot SHAP summary visualization.

    Creates a SHAP summary plot showing feature importance and
    the direction of feature effects.

    Args:
        shap_values: SHAP values array (n_samples, n_features) or list for multi-class
        features: Feature values (DataFrame or ndarray)
        feature_names: List of feature names (optional if features is DataFrame)
        max_display: Maximum features to display
        title: Plot title
        plot_type: Type of plot ('dot', 'bar', 'violin')
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Note:
        Requires SHAP library. Falls back to bar plot of mean |SHAP| if unavailable.
    """
    apply_publication_style()

    # Get feature names
    if feature_names is None:
        if isinstance(features, pd.DataFrame):
            feature_names = features.columns.tolist()
        else:
            feature_names = [f"Feature {i}" for i in range(features.shape[1])]

    fig, ax = plt.subplots(figsize=figsize)

    if HAS_SHAP:
        try:
            # Use SHAP's built-in plotting
            plt.figure(fig.number)

            if plot_type == "dot":
                shap.summary_plot(
                    shap_values,
                    features,
                    feature_names=feature_names,
                    max_display=max_display,
                    show=False,
                    plot_type="dot"
                )
            elif plot_type == "bar":
                shap.summary_plot(
                    shap_values,
                    features,
                    feature_names=feature_names,
                    max_display=max_display,
                    show=False,
                    plot_type="bar"
                )
            elif plot_type == "violin":
                shap.summary_plot(
                    shap_values,
                    features,
                    feature_names=feature_names,
                    max_display=max_display,
                    show=False,
                    plot_type="violin"
                )

            # Get the current figure (SHAP creates its own)
            fig = plt.gcf()
            fig.suptitle(title, y=1.02)

            return fig

        except Exception as e:
            logger.warning(f"SHAP plotting failed, falling back to bar plot: {e}")

    # Fallback: simple bar plot of mean |SHAP|
    if len(shap_values.shape) == 3:
        # Multi-class: average across classes
        mean_shap = np.abs(shap_values).mean(axis=(0, 2))
    else:
        mean_shap = np.abs(shap_values).mean(axis=0)

    # Sort by importance
    sorted_idx = np.argsort(mean_shap)[::-1][:max_display]

    y_pos = np.arange(len(sorted_idx))

    ax.barh(y_pos, mean_shap[sorted_idx][::-1], color=AUTOML_COLORS['primary'])
    ax.set_yticks(y_pos)
    ax.set_yticklabels([feature_names[i] for i in sorted_idx[::-1]])
    ax.set_xlabel('Mean |SHAP value|')
    ax.set_title(title)

    plt.tight_layout()

    return fig


def plot_shap_waterfall(
    shap_values: np.ndarray,
    features: Union[pd.DataFrame, pd.Series, np.ndarray],
    feature_names: Optional[List[str]] = None,
    expected_value: Optional[float] = None,
    sample_idx: int = 0,
    max_display: int = 15,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 8),
) -> plt.Figure:
    """
    Plot SHAP waterfall for a single prediction.

    Shows how each feature contributes to push the prediction
    from the base value to the final prediction.

    Args:
        shap_values: SHAP values for the sample
        features: Feature values
        feature_names: List of feature names
        expected_value: Base/expected value (E[f(x)])
        sample_idx: Index of sample to explain (if shap_values is 2D)
        max_display: Maximum features to show
        title: Plot title
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    # Get feature names
    if feature_names is None:
        if isinstance(features, pd.DataFrame):
            feature_names = features.columns.tolist()
        elif isinstance(features, pd.Series):
            feature_names = features.index.tolist()
        else:
            n_features = features.shape[1] if len(features.shape) > 1 else len(features)
            feature_names = [f"Feature {i}" for i in range(n_features)]

    # Extract single sample SHAP values
    if len(shap_values.shape) == 2:
        sample_shap = shap_values[sample_idx]
    else:
        sample_shap = shap_values

    # Get feature values for this sample
    if isinstance(features, pd.DataFrame):
        sample_features = features.iloc[sample_idx].values
    elif isinstance(features, pd.Series):
        sample_features = features.values
    else:
        if len(features.shape) == 2:
            sample_features = features[sample_idx]
        else:
            sample_features = features

    fig, ax = plt.subplots(figsize=figsize)

    if HAS_SHAP and expected_value is not None:
        try:
            # Use SHAP's waterfall plot
            plt.figure(fig.number)

            explanation = shap.Explanation(
                values=sample_shap,
                base_values=expected_value,
                data=sample_features,
                feature_names=feature_names,
            )

            shap.waterfall_plot(explanation, max_display=max_display, show=False)

            fig = plt.gcf()
            if title:
                fig.suptitle(title, y=1.02)

            return fig

        except Exception as e:
            logger.warning(f"SHAP waterfall failed, falling back to bar plot: {e}")

    # Fallback: simple contribution bar plot
    contributions = pd.DataFrame({
        'feature': feature_names,
        'shap': sample_shap,
        'value': sample_features,
    })

    # Sort by absolute SHAP value
    contributions['abs_shap'] = np.abs(contributions['shap'])
    contributions = contributions.sort_values('abs_shap', ascending=True).tail(max_display)

    # Colors based on sign
    colors = [AUTOML_COLORS['positive'] if s > 0 else AUTOML_COLORS['negative']
              for s in contributions['shap']]

    y_pos = np.arange(len(contributions))

    ax.barh(y_pos, contributions['shap'], color=colors, edgecolor='black', linewidth=0.5)
    ax.set_yticks(y_pos)

    # Show feature name and value
    labels = [f"{f} = {v:.2f}" if isinstance(v, (int, float)) else f"{f} = {v}"
              for f, v in zip(contributions['feature'], contributions['value'], strict=False)]
    ax.set_yticklabels(labels)

    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.set_xlabel('SHAP Value (contribution to prediction)')
    ax.set_title(title or 'Feature Contributions to Prediction')

    # Add legend
    pos_patch = mpatches.Patch(color=AUTOML_COLORS['positive'], label='Increases prediction')
    neg_patch = mpatches.Patch(color=AUTOML_COLORS['negative'], label='Decreases prediction')
    ax.legend(handles=[pos_patch, neg_patch], loc='lower right')

    plt.tight_layout()

    return fig


# =============================================================================
# Learning Curve Plot
# =============================================================================

def plot_learning_curve(
    train_sizes: np.ndarray,
    train_scores: np.ndarray,
    val_scores: np.ndarray,
    train_std: Optional[np.ndarray] = None,
    val_std: Optional[np.ndarray] = None,
    title: str = "Learning Curve",
    xlabel: str = "Training Examples",
    ylabel: str = "Score",
    figsize: Tuple[float, float] = (8, 6),
) -> plt.Figure:
    """
    Plot learning curve showing train and validation performance.

    Helps diagnose bias-variance tradeoff:
    - High gap between train/val = overfitting
    - Both low = underfitting
    - Both high, converging = good fit

    Args:
        train_sizes: Array of training set sizes
        train_scores: Training scores at each size
        val_scores: Validation scores at each size
        train_std: Optional std dev for training scores
        val_std: Optional std dev for validation scores
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    fig, ax = plt.subplots(figsize=figsize)

    # Plot training scores
    ax.plot(train_sizes, train_scores, 'o-', color=AUTOML_COLORS['primary'],
            label='Training Score', linewidth=2, markersize=6)

    if train_std is not None:
        ax.fill_between(train_sizes,
                        train_scores - train_std,
                        train_scores + train_std,
                        alpha=0.2, color=AUTOML_COLORS['primary'])

    # Plot validation scores
    ax.plot(train_sizes, val_scores, 'o-', color=AUTOML_COLORS['secondary'],
            label='Validation Score', linewidth=2, markersize=6)

    if val_std is not None:
        ax.fill_between(train_sizes,
                        val_scores - val_std,
                        val_scores + val_std,
                        alpha=0.2, color=AUTOML_COLORS['secondary'])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    # Add diagnosis annotation
    final_gap = train_scores[-1] - val_scores[-1]
    if final_gap > 0.1:
        diagnosis = "⚠️ Possible overfitting (large train-val gap)"
    elif train_scores[-1] < 0.7 and val_scores[-1] < 0.7:
        diagnosis = "⚠️ Possible underfitting (both scores low)"
    else:
        diagnosis = "✓ Model appears well-fitted"

    ax.text(0.02, 0.02, diagnosis, transform=ax.transAxes,
            fontsize=10, verticalalignment='bottom',
            bbox={'boxstyle': 'round', 'facecolor': 'white', 'alpha': 0.8})

    plt.tight_layout()

    return fig


# =============================================================================
# Model Comparison / Leaderboard Plot
# =============================================================================

def plot_model_comparison(
    leaderboard: Union[List[Dict], pd.DataFrame],
    metric: str = "score",
    metric_name: Optional[str] = None,
    top_n: int = 10,
    title: str = "Model Comparison",
    show_time: bool = True,
    figsize: Optional[Tuple[float, float]] = None,
) -> plt.Figure:
    """
    Plot model comparison from AutoML leaderboard.

    Creates a horizontal bar chart comparing model performance,
    optionally showing training time.

    Args:
        leaderboard: List of dicts or DataFrame with model results
            Required columns: 'model_name', metric (e.g., 'score')
            Optional: 'fit_time', 'pred_time'
        metric: Column name for the performance metric
        metric_name: Display name for metric (default: use column name)
        top_n: Number of top models to show
        title: Plot title
        show_time: Show training time as secondary axis
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    # Convert to DataFrame
    if isinstance(leaderboard, list):
        df = pd.DataFrame(leaderboard)
    else:
        df = leaderboard.copy()

    # Handle different column naming conventions
    name_col = 'model_name' if 'model_name' in df.columns else 'model'
    score_col = metric if metric in df.columns else 'score'

    # Sort and take top N
    df = df.sort_values(score_col, ascending=False).head(top_n)
    df = df.sort_values(score_col, ascending=True)  # Reverse for horizontal bar

    # Determine figure size
    if figsize is None:
        figsize = (10, max(4, len(df) * 0.5))

    fig, ax1 = plt.subplots(figsize=figsize)

    y_pos = np.arange(len(df))

    # Get colors based on model type
    colors = [_get_model_color(name) for name in df[name_col]]

    # Plot performance bars
    bars = ax1.barh(y_pos, df[score_col], color=colors, edgecolor='black', linewidth=0.5)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(df[name_col])
    ax1.set_xlabel(metric_name or metric.replace('_', ' ').title())
    ax1.set_title(title)

    # Show values on bars
    for bar, val in zip(bars, df[score_col], strict=False):
        ax1.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                f'{val:.4f}', va='center', fontsize=9)

    # Add training time as secondary axis
    if show_time and 'fit_time' in df.columns:
        ax2 = ax1.twiny()
        ax2.plot(df['fit_time'], y_pos, 'D--', color=AUTOML_COLORS['neutral'],
                markersize=6, alpha=0.7, label='Fit Time')
        ax2.set_xlabel('Training Time (s)', color=AUTOML_COLORS['neutral'])
        ax2.tick_params(axis='x', colors=AUTOML_COLORS['neutral'])

    # Highlight best model
    best_idx = len(df) - 1  # Last one is best (after sorting)
    bars[best_idx].set_edgecolor(AUTOML_COLORS['positive'])
    bars[best_idx].set_linewidth(3)

    plt.tight_layout()

    return fig


def plot_algorithm_performance(
    results: Dict[str, Dict[str, float]],
    metrics: Optional[List[str]] = None,
    title: str = "Algorithm Performance Comparison",
    figsize: Tuple[float, float] = (12, 6),
) -> plt.Figure:
    """
    Plot grouped bar chart comparing algorithms across multiple metrics.

    Args:
        results: Dict of {algorithm: {metric: value}}
        metrics: List of metrics to show
        title: Plot title
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    if metrics is None:
        metrics = ['accuracy', 'f1', 'auc']
    apply_publication_style()

    fig, ax = plt.subplots(figsize=figsize)

    algorithms = list(results.keys())
    n_algorithms = len(algorithms)
    n_metrics = len(metrics)

    x = np.arange(n_algorithms)
    width = 0.8 / n_metrics

    colors = sns.color_palette("Set2", n_metrics)

    for i, metric in enumerate(metrics):
        values = [results[alg].get(metric, 0) for alg in algorithms]
        offset = (i - n_metrics/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=metric.upper(),
                     color=colors[i], edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Algorithm')
    ax.set_ylabel('Score')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(algorithms, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 1.1)

    plt.tight_layout()

    return fig


# =============================================================================
# Prediction vs Actual Plot (for Regression)
# =============================================================================

def plot_prediction_vs_actual(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str = "Prediction vs Actual",
    xlabel: str = "Actual",
    ylabel: str = "Predicted",
    show_metrics: bool = True,
    figsize: Tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Plot predicted vs actual values for regression.

    Includes:
    - Scatter plot of predictions
    - Perfect prediction line (y=x)
    - R² and RMSE metrics

    Args:
        y_true: Actual values
        y_pred: Predicted values
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        show_metrics: Show R² and RMSE
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    fig, ax = plt.subplots(figsize=figsize)

    # Scatter plot
    ax.scatter(y_true, y_pred, alpha=0.5, color=AUTOML_COLORS['primary'], s=20)

    # Perfect prediction line
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect Prediction')

    # Fit line
    z = np.polyfit(y_true, y_pred, 1)
    p = np.poly1d(z)
    ax.plot([min_val, max_val], [p(min_val), p(max_val)],
            color=AUTOML_COLORS['secondary'], linewidth=2, label='Fit Line')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()

    # Add metrics
    if show_metrics:
        # Calculate R² and RMSE
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = np.mean(np.abs(y_true - y_pred))

        metrics_text = f"R² = {r2:.4f}\nRMSE = {rmse:.4f}\nMAE = {mae:.4f}"
        ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes,
                verticalalignment='top', fontsize=10,
                bbox={'boxstyle': 'round', 'facecolor': 'white', 'alpha': 0.8})

    plt.tight_layout()

    return fig


# =============================================================================
# Residual Plot (for Regression)
# =============================================================================

def plot_residuals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str = "Residual Plot",
    figsize: Tuple[float, float] = (10, 4),
) -> plt.Figure:
    """
    Plot residuals for regression model.

    Shows:
    - Residuals vs predicted values
    - Histogram of residuals

    Args:
        y_true: Actual values
        y_pred: Predicted values
        title: Plot title
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    apply_publication_style()

    residuals = y_true - y_pred

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Residuals vs Predicted
    ax1.scatter(y_pred, residuals, alpha=0.5, color=AUTOML_COLORS['primary'], s=20)
    ax1.axhline(y=0, color='red', linestyle='--', linewidth=2)
    ax1.set_xlabel('Predicted')
    ax1.set_ylabel('Residual')
    ax1.set_title('Residuals vs Predicted')

    # Histogram of residuals
    ax2.hist(residuals, bins=30, color=AUTOML_COLORS['primary'],
             edgecolor='black', alpha=0.7)
    ax2.axvline(x=0, color='red', linestyle='--', linewidth=2)
    ax2.set_xlabel('Residual')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Residual Distribution')

    # Add normality info
    mean_res = np.mean(residuals)
    std_res = np.std(residuals)
    ax2.text(0.95, 0.95, f'Mean: {mean_res:.4f}\nStd: {std_res:.4f}',
             transform=ax2.transAxes, ha='right', va='top',
             bbox={'boxstyle': 'round', 'facecolor': 'white', 'alpha': 0.8})

    fig.suptitle(title)
    plt.tight_layout()

    return fig


# =============================================================================
# High-Level Visualization Creator
# =============================================================================

def create_automl_visualizations(
    model_result: Dict[str, Any],
    X: Optional[pd.DataFrame] = None,
    y_true: Optional[np.ndarray] = None,
    y_pred: Optional[np.ndarray] = None,
    shap_values: Optional[np.ndarray] = None,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    save_to_minio: bool = True,
) -> List[VisualizationResult]:
    """
    Create visualizations for AutoML training results.

    Automatically generates appropriate plots based on available data:
    - Feature importance (if available)
    - Model comparison/leaderboard
    - SHAP plots (if SHAP values provided)
    - Prediction plots (if predictions provided)

    Args:
        model_result: AutoML result dict containing:
            - feature_importance: Dict[str, float]
            - leaderboard: List of model scores
            - problem_type: 'binary', 'multiclass', 'regression'
        X: Feature DataFrame (for SHAP plots)
        y_true: True target values (for prediction plots)
        y_pred: Predicted values
        shap_values: SHAP values array
        user_id: User ID for MinIO storage
        job_id: Job ID for MinIO storage
        save_to_minio: Whether to save to MinIO

    Returns:
        List of VisualizationResult objects
    """
    results = []

    try:
        # 1. Feature Importance Plot
        feature_importance = model_result.get('feature_importance', {})
        if feature_importance:
            fig = plot_feature_importance(
                feature_importance,
                title="Feature Importance"
            )

            viz_result = VisualizationResult(
                type=VisualizationType.FEATURE_IMPORTANCE,
                url="",
                title="Feature Importance",
                description=f"Top {min(20, len(feature_importance))} most important features",
            )

            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "feature_importance.png", user_id, job_id)
                viz_result.url = url

            results.append(viz_result)
            plt.close(fig)

        # 2. Model Leaderboard Plot
        leaderboard = model_result.get('leaderboard', [])
        if leaderboard:
            metric = model_result.get('metric', 'score')

            fig = plot_model_comparison(
                leaderboard,
                metric='score',
                metric_name=metric,
                title=f"Model Comparison ({metric})"
            )

            viz_result = VisualizationResult(
                type=VisualizationType.MODEL_COMPARISON,
                url="",
                title="Model Leaderboard",
                description=f"Comparison of {len(leaderboard)} trained models",
            )

            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "model_comparison.png", user_id, job_id)
                viz_result.url = url

            results.append(viz_result)
            plt.close(fig)

        # 3. SHAP Summary Plot
        if shap_values is not None and X is not None:
            fig = plot_shap_summary(
                shap_values,
                X,
                title="SHAP Feature Importance"
            )

            viz_result = VisualizationResult(
                type=VisualizationType.SHAP_SUMMARY,
                url="",
                title="SHAP Summary",
                description="Feature importance based on SHAP values",
            )

            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "shap_summary.png", user_id, job_id)
                viz_result.url = url

            results.append(viz_result)
            plt.close(fig)

        # 4. Prediction vs Actual (for regression)
        problem_type = model_result.get('problem_type', '')
        if y_true is not None and y_pred is not None and 'regression' in problem_type.lower():
            fig = plot_prediction_vs_actual(y_true, y_pred)

            viz_result = VisualizationResult(
                type=VisualizationType.SCATTER_PLOT,
                url="",
                title="Prediction vs Actual",
                description="Predicted values compared to actual values",
            )

            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "prediction_vs_actual.png", user_id, job_id)
                viz_result.url = url

            results.append(viz_result)
            plt.close(fig)

            # Also add residual plot for regression
            fig = plot_residuals(y_true, y_pred)

            viz_result = VisualizationResult(
                type=VisualizationType.CUSTOM,
                url="",
                title="Residual Analysis",
                description="Residual distribution and patterns",
            )

            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "residual_plot.png", user_id, job_id)
                viz_result.url = url

            results.append(viz_result)
            plt.close(fig)

    except Exception as e:
        logger.error(f"Failed to create AutoML visualizations: {e}")

    return results

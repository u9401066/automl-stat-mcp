"""
Visualization Module

Provides plotting utilities for statistical analysis results.
Generates publication-quality figures and uploads to MinIO.

Components:
    - storage: MinIO upload utilities
    - style: Publication-ready matplotlib styles
    - schemas: Visualization result data structures
    - survival: Survival analysis plots (KM, forest)
    - roc: ROC/PR curve plots
    - group_comparison: Group comparison plots (t-test, ANOVA, chi-square)
    - automl: AutoML training result plots (SHAP, feature importance, leaderboard)
"""

from .automl import (
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
from .group_comparison import (
    create_group_comparison_visualizations,
    plot_anova_results,
    plot_categorical_comparison,
    plot_contingency_heatmap,
    plot_correlation_heatmap,
    plot_group_comparison,
    plot_ttest_result,
)
from .roc import (
    create_roc_visualizations,
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_pr_curve,
    plot_roc_curve,
    plot_roc_curves_comparison,
    plot_threshold_analysis,
)
from .schemas import (
    GroupComparisonVisualizationResult,
    ROCVisualizationResult,
    SurvivalVisualizationResult,
    VisualizationBundle,
    VisualizationConfig,
    VisualizationResult,
    VisualizationType,
)
from .storage import get_figure_url, save_figure_to_minio, save_multiple_figures
from .style import (
    CLINICAL_COLORS,
    PUBLICATION_STYLE,
    ROC_COLORS,
    SURVIVAL_COLORS,
    apply_publication_style,
    get_figure_with_style,
    style_forest_plot,
    style_roc_plot,
    style_survival_plot,
)
from .survival import (
    create_survival_visualizations,
    plot_cumulative_hazard,
    plot_forest_plot,
    plot_hazard_ratio,
    plot_kaplan_meier,
)

__all__ = [
    # Storage
    "save_figure_to_minio",
    "get_figure_url",
    "save_multiple_figures",
    # Style
    "apply_publication_style",
    "PUBLICATION_STYLE",
    "CLINICAL_COLORS",
    "ROC_COLORS",
    "SURVIVAL_COLORS",
    "get_figure_with_style",
    "style_roc_plot",
    "style_survival_plot",
    "style_forest_plot",
    # Schemas
    "VisualizationResult",
    "VisualizationType",
    "VisualizationBundle",
    "VisualizationConfig",
    "ROCVisualizationResult",
    "SurvivalVisualizationResult",
    "GroupComparisonVisualizationResult",
    # Survival plots
    "plot_kaplan_meier",
    "plot_cumulative_hazard",
    "plot_forest_plot",
    "plot_hazard_ratio",
    "create_survival_visualizations",
    # ROC plots
    "plot_roc_curve",
    "plot_roc_curves_comparison",
    "plot_pr_curve",
    "plot_calibration_curve",
    "plot_confusion_matrix",
    "plot_threshold_analysis",
    "create_roc_visualizations",
    # Group comparison plots
    "plot_group_comparison",
    "plot_anova_results",
    "plot_contingency_heatmap",
    "plot_categorical_comparison",
    "plot_correlation_heatmap",
    "plot_ttest_result",
    "create_group_comparison_visualizations",
    # AutoML plots
    "plot_feature_importance",
    "plot_shap_summary",
    "plot_shap_waterfall",
    "plot_learning_curve",
    "plot_model_comparison",
    "plot_algorithm_performance",
    "plot_prediction_vs_actual",
    "plot_residuals",
    "create_automl_visualizations",
]

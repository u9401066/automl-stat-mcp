"""
Visualization Schema Definitions

Data classes and enums for standardized visualization results.

Usage:
    from visualization.schemas import VisualizationResult, VisualizationType

    result = VisualizationResult(
        type=VisualizationType.ROC_CURVE,
        url="https://minio.example.com/stats-reports/user123/job456/roc_curve.png",
        title="ROC Curve",
        description="AUC = 0.85 (95% CI: 0.80-0.90)"
    )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VisualizationType(str, Enum):
    """Types of visualizations supported by the system."""

    # ROC Analysis
    ROC_CURVE = "roc_curve"
    PR_CURVE = "pr_curve"
    CALIBRATION_CURVE = "calibration_curve"
    THRESHOLD_ANALYSIS = "threshold_analysis"

    # Survival Analysis
    KAPLAN_MEIER = "kaplan_meier"
    FOREST_PLOT = "forest_plot"
    HAZARD_RATIO_PLOT = "hazard_ratio_plot"
    CUMULATIVE_HAZARD = "cumulative_hazard"

    # Group Comparison
    BOXPLOT = "boxplot"
    VIOLIN_PLOT = "violin_plot"
    BAR_CHART = "bar_chart"
    STRIP_PLOT = "strip_plot"

    # Correlation & Relationships
    HEATMAP = "heatmap"
    CORRELATION_MATRIX = "correlation_matrix"
    SCATTER_PLOT = "scatter_plot"

    # Distribution
    HISTOGRAM = "histogram"
    DENSITY_PLOT = "density_plot"
    QQ_PLOT = "qq_plot"

    # EDA / Summary
    MISSING_VALUES = "missing_values"
    FEATURE_IMPORTANCE = "feature_importance"

    # AutoML Specific
    MODEL_COMPARISON = "model_comparison"
    SHAP_SUMMARY = "shap_summary"
    SHAP_WATERFALL = "shap_waterfall"
    LEARNING_CURVE = "learning_curve"
    CONFUSION_MATRIX = "confusion_matrix"

    # Other
    CUSTOM = "custom"


@dataclass
class VisualizationResult:
    """
    Standardized visualization result structure.

    Attributes:
        type: Type of visualization (enum)
        url: URL to access the image (MinIO presigned or direct)
        title: Display title for the visualization
        description: Brief description or key findings
        metadata: Additional metadata (e.g., AUC value, p-value, etc.)
        format: Image format (png, svg, pdf)
        width: Image width in pixels
        height: Image height in pixels
    """

    type: VisualizationType
    url: str
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    format: str = "png"
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata or {},
            "format": self.format,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualizationResult":
        """Create instance from dictionary."""
        return cls(
            type=VisualizationType(data["type"]),
            url=data["url"],
            title=data["title"],
            description=data.get("description"),
            metadata=data.get("metadata", {}),
            format=data.get("format", "png"),
            width=data.get("width"),
            height=data.get("height"),
        )


@dataclass
class VisualizationBundle:
    """
    Collection of related visualizations from a single analysis.

    Attributes:
        job_id: Associated job ID
        user_id: User who created the visualizations
        visualizations: List of visualization results
        created_at: ISO timestamp of creation
    """

    job_id: str
    user_id: str
    visualizations: List[VisualizationResult] = field(default_factory=list)
    created_at: Optional[str] = None

    def add(self, visualization: VisualizationResult) -> None:
        """Add a visualization to the bundle."""
        self.visualizations.append(visualization)

    def get_by_type(self, viz_type: VisualizationType) -> List[VisualizationResult]:
        """Get all visualizations of a specific type."""
        return [v for v in self.visualizations if v.type == viz_type]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "visualizations": [v.to_dict() for v in self.visualizations],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualizationBundle":
        """Create instance from dictionary."""
        return cls(
            job_id=data["job_id"],
            user_id=data["user_id"],
            visualizations=[VisualizationResult.from_dict(v) for v in data.get("visualizations", [])],
            created_at=data.get("created_at"),
        )


# =============================================================================
# Visualization Configuration
# =============================================================================


@dataclass
class VisualizationConfig:
    """
    Configuration options for generating visualizations.

    Attributes:
        dpi: Output resolution (default: 300 for publication)
        format: Output format (png, svg, pdf)
        width: Figure width in inches
        height: Figure height in inches
        style: Style preset to use
        transparent: Whether background should be transparent
        include_title: Whether to include title in the figure
    """

    dpi: int = 300
    format: str = "png"
    width: float = 8.0
    height: float = 6.0
    style: str = "publication"
    transparent: bool = False
    include_title: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dpi": self.dpi,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "style": self.style,
            "transparent": self.transparent,
            "include_title": self.include_title,
        }


# =============================================================================
# Analysis-Specific Result Extensions
# =============================================================================


@dataclass
class ROCVisualizationResult(VisualizationResult):
    """ROC curve visualization with additional metrics."""

    auc: Optional[float] = None
    auc_ci_lower: Optional[float] = None
    auc_ci_upper: Optional[float] = None
    optimal_threshold: Optional[float] = None

    def __post_init__(self):
        self.type = VisualizationType.ROC_CURVE
        # Add AUC to metadata
        if self.auc is not None:
            self.metadata = self.metadata or {}
            self.metadata["auc"] = self.auc
            if self.auc_ci_lower is not None and self.auc_ci_upper is not None:
                self.metadata["auc_ci"] = [self.auc_ci_lower, self.auc_ci_upper]
            if self.optimal_threshold is not None:
                self.metadata["optimal_threshold"] = self.optimal_threshold


@dataclass
class SurvivalVisualizationResult(VisualizationResult):
    """Survival curve visualization with additional metrics."""

    median_survival: Optional[float] = None
    hazard_ratio: Optional[float] = None
    hr_ci_lower: Optional[float] = None
    hr_ci_upper: Optional[float] = None
    p_value: Optional[float] = None

    def __post_init__(self):
        self.type = VisualizationType.KAPLAN_MEIER
        # Add metrics to metadata
        self.metadata = self.metadata or {}
        if self.median_survival is not None:
            self.metadata["median_survival"] = self.median_survival
        if self.hazard_ratio is not None:
            self.metadata["hazard_ratio"] = self.hazard_ratio
        if self.hr_ci_lower is not None and self.hr_ci_upper is not None:
            self.metadata["hr_ci"] = [self.hr_ci_lower, self.hr_ci_upper]
        if self.p_value is not None:
            self.metadata["p_value"] = self.p_value


@dataclass
class GroupComparisonVisualizationResult(VisualizationResult):
    """Group comparison visualization with statistical annotation."""

    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    test_name: Optional[str] = None

    def __post_init__(self):
        # Add metrics to metadata
        self.metadata = self.metadata or {}
        if self.p_value is not None:
            self.metadata["p_value"] = self.p_value
        if self.effect_size is not None:
            self.metadata["effect_size"] = self.effect_size
        if self.test_name is not None:
            self.metadata["test_name"] = self.test_name

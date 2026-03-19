"""
ROC/AUC Analysis Package

Domain-driven modular structure for classifier evaluation.

Submodules:
    - types: Data classes for ROC results
    - core: ROCAnalyzer and DeLongTest
    - calibration: CalibrationAnalyzer
    - precision_recall: PrecisionRecallAnalyzer and NetBenefitAnalyzer
    - functions: Convenience functions for MCP tools
"""

from .calibration import CalibrationAnalyzer
from .core import (
    DeLongTest,
    ROCAnalyzer,
)
from .functions import (
    analyze_calibration,
    compare_multiple_models,
    compare_roc_curves,
    compute_precision_recall,
    compute_roc_curve,
    find_optimal_threshold,
    full_classifier_evaluation,
    generate_publication_report,
    threshold_analysis,
)
from .precision_recall import (
    NetBenefitAnalyzer,
    PrecisionRecallAnalyzer,
)
from .types import (
    AUCComparisonResult,
    CalibrationResult,
    PrecisionRecallResult,
    ROCCurveResult,
    ROCPoint,
)

__all__ = [
    # Types
    "ROCPoint",
    "ROCCurveResult",
    "AUCComparisonResult",
    "CalibrationResult",
    "PrecisionRecallResult",
    # Core analyzers
    "ROCAnalyzer",
    "DeLongTest",
    "CalibrationAnalyzer",
    "PrecisionRecallAnalyzer",
    "NetBenefitAnalyzer",
    # Functions
    "compute_roc_curve",
    "compare_roc_curves",
    "analyze_calibration",
    "compute_precision_recall",
    "find_optimal_threshold",
    "full_classifier_evaluation",
    "compare_multiple_models",
    "threshold_analysis",
    "generate_publication_report",
]

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
from .types import (
    ROCPoint,
    ROCCurveResult,
    AUCComparisonResult,
    CalibrationResult,
    PrecisionRecallResult,
)
from .core import (
    ROCAnalyzer,
    DeLongTest,
)
from .calibration import CalibrationAnalyzer
from .precision_recall import (
    PrecisionRecallAnalyzer,
    NetBenefitAnalyzer,
)
from .functions import (
    compute_roc_curve,
    compare_roc_curves,
    analyze_calibration,
    compute_precision_recall,
    find_optimal_threshold,
    full_classifier_evaluation,
    compare_multiple_models,
    threshold_analysis,
    generate_publication_report,
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

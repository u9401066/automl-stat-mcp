"""
ROC/AUC Analysis - Backward Compatibility Wrapper

This file re-exports all classes and functions from the roc/ package
for backward compatibility. All new development should use the modular
roc/ package directly.

Package structure:
    roc/
    ├── __init__.py        - Package exports
    ├── types.py           - Data classes (ROCPoint, ROCCurveResult, etc.)
    ├── core.py            - ROCAnalyzer, DeLongTest
    ├── calibration.py     - CalibrationAnalyzer
    ├── precision_recall.py - PrecisionRecallAnalyzer, NetBenefitAnalyzer
    └── functions.py       - Convenience and advanced functions
"""

# Re-export everything from the roc package for backward compatibility
from .roc import (
    AUCComparisonResult,
    CalibrationAnalyzer,
    CalibrationResult,
    DeLongTest,
    NetBenefitAnalyzer,
    PrecisionRecallAnalyzer,
    PrecisionRecallResult,
    # Core analyzers
    ROCAnalyzer,
    ROCCurveResult,
    # Types
    ROCPoint,
    analyze_calibration,
    compare_multiple_models,
    compare_roc_curves,
    compute_precision_recall,
    # Functions
    compute_roc_curve,
    find_optimal_threshold,
    full_classifier_evaluation,
    generate_publication_report,
    threshold_analysis,
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

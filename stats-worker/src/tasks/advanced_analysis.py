"""
Advanced Statistical Analysis - Backward Compatibility Wrapper

This file re-exports all classes and functions from the analysis/ package
for backward compatibility. All new development should use the modular
analysis/ package directly.

Package structure:
    analysis/
    ├── __init__.py           - Package exports
    ├── base.py               - Common utilities (safe_round)
    ├── correlation.py        - Enhanced correlation analysis
    ├── distribution.py       - Distribution comparison tests
    ├── missing_data.py       - Missing value analysis (MCAR/MAR/MNAR)
    ├── multicollinearity.py  - VIF analysis
    └── functions.py          - Convenience functions
"""
# Re-export everything from the analysis package for backward compatibility
from .analysis import (
    # Base
    safe_round,
    # Correlation
    CorrelationPair,
    EnhancedCorrelationResult,
    compute_enhanced_correlation,
    # Distribution
    DistributionComparisonResult,
    GroupComparisonResult,
    compare_distributions,
    ks_test_two_samples,
    # Missing data
    MissingValueAnalysis,
    analyze_missing_values,
    # Multicollinearity
    VIFResult,
    MulticollinearityAnalysis,
    compute_vif,
    # Functions
    run_enhanced_analysis,
)

__all__ = [
    # Base
    "safe_round",
    # Correlation
    "CorrelationPair",
    "EnhancedCorrelationResult",
    "compute_enhanced_correlation",
    # Distribution
    "DistributionComparisonResult",
    "GroupComparisonResult",
    "compare_distributions",
    "ks_test_two_samples",
    # Missing data
    "MissingValueAnalysis",
    "analyze_missing_values",
    # Multicollinearity
    "VIFResult",
    "MulticollinearityAnalysis",
    "compute_vif",
    # Functions
    "run_enhanced_analysis",
]

"""
Advanced Analysis Package

Domain-driven modular structure for advanced statistical analysis.

Submodules:
    - base: Common utilities and safe_round
    - correlation: Enhanced correlation analysis
    - distribution: Distribution comparison tests
    - missing_data: Missing value analysis (MCAR/MAR/MNAR)
    - multicollinearity: VIF analysis
"""
from .base import safe_round
from .correlation import (
    CorrelationPair,
    EnhancedCorrelationResult,
    compute_enhanced_correlation,
)
from .distribution import (
    DistributionComparisonResult,
    GroupComparisonResult,
    compare_distributions,
    ks_test_two_samples,
)
from .functions import run_enhanced_analysis
from .missing_data import (
    MissingValueAnalysis,
    analyze_missing_values,
)
from .multicollinearity import (
    MulticollinearityAnalysis,
    VIFResult,
    compute_vif,
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

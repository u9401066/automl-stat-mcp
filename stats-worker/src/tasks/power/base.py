"""
Power Analysis Base Module

Shared types, constants, and helper functions for power analysis.

Contains:
    - EffectSizeType: Effect size type enumeration
    - TestType: Statistical test type enumeration
    - PowerAnalysisResult: Result dataclass for power calculations
    - Helper functions for effect size calculations
"""
import logging
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportion_effectsize

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class EffectSizeType(str, Enum):
    """Effect size types"""
    COHENS_D = "Cohen's d"
    COHENS_H = "Cohen's h"
    COHENS_F = "Cohen's f"
    CORRELATION_R = "Correlation r"
    ODDS_RATIO = "Odds Ratio"
    RISK_RATIO = "Risk Ratio"
    HAZARD_RATIO = "Hazard Ratio"


class TestType(str, Enum):
    """Statistical test types"""
    TTEST_IND = "two-sample t-test"
    TTEST_PAIRED = "paired t-test"
    TTEST_ONE = "one-sample t-test"
    PROPORTION_TWO = "two proportions test"
    PROPORTION_ONE = "one proportion test"


# Effect size interpretation thresholds (Cohen's conventions)
EFFECT_SIZE_THRESHOLDS = {
    "cohens_d": {"small": 0.2, "medium": 0.5, "large": 0.8},
    "cohens_h": {"small": 0.2, "medium": 0.5, "large": 0.8},
    "cohens_f": {"small": 0.1, "medium": 0.25, "large": 0.4},
    "correlation_r": {"small": 0.1, "medium": 0.3, "large": 0.5},
}


# =============================================================================
# Helper Functions
# =============================================================================

def safe_round(value: Optional[float], decimals: int = 4) -> Optional[float]:
    """
    Round a value safely, returning None for NaN/Inf.
    
    Args:
        value: The value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value or None if invalid
    """
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def interpret_effect_size(
    effect_size: float,
    effect_type: str = "cohens_d"
) -> str:
    """
    Interpret effect size magnitude based on Cohen's conventions.
    
    Args:
        effect_size: The effect size value (absolute)
        effect_type: Type of effect size
        
    Returns:
        Interpretation string: "negligible", "small", "medium", "large"
    """
    abs_es = abs(effect_size)
    thresholds = EFFECT_SIZE_THRESHOLDS.get(effect_type, EFFECT_SIZE_THRESHOLDS["cohens_d"])
    
    if abs_es < thresholds["small"]:
        return "negligible"
    elif abs_es < thresholds["medium"]:
        return "small"
    elif abs_es < thresholds["large"]:
        return "medium"
    else:
        return "large"


def cohens_d_from_means(
    mean1: float,
    mean2: float,
    sd1: float,
    sd2: Optional[float] = None,
    pooled: bool = True
) -> float:
    """
    Calculate Cohen's d from means and standard deviations.
    
    Args:
        mean1: Mean of group 1
        mean2: Mean of group 2
        sd1: Standard deviation of group 1
        sd2: Standard deviation of group 2 (if None, uses sd1)
        pooled: Whether to use pooled SD (recommended for independent samples)
        
    Returns:
        Cohen's d effect size
    """
    if sd2 is None:
        sd2 = sd1
    
    if pooled:
        # Pooled standard deviation (assumes equal sample sizes for simplicity)
        pooled_sd = math.sqrt((sd1**2 + sd2**2) / 2)
    else:
        pooled_sd = sd1
    
    if pooled_sd == 0:
        return 0.0
    
    return (mean1 - mean2) / pooled_sd


def cohens_h_from_proportions(p1: float, p2: float) -> float:
    """
    Calculate Cohen's h from two proportions.
    
    Cohen's h = 2 * (arcsin(sqrt(p1)) - arcsin(sqrt(p2)))
    
    Args:
        p1: Proportion in group 1
        p2: Proportion in group 2
        
    Returns:
        Cohen's h effect size
    """
    return proportion_effectsize(p1, p2)


# =============================================================================
# Result Dataclasses
# =============================================================================

@dataclass
class PowerAnalysisResult:
    """Result of power analysis calculation"""
    
    # Test identification
    test_type: str
    scenario: str  # "sample_size" or "power"
    
    # Main results
    sample_size_per_group: Optional[int] = None
    total_sample_size: Optional[int] = None
    power: Optional[float] = None
    
    # Input parameters
    effect_size: Optional[float] = None
    effect_size_type: str = "Cohen's d"
    effect_size_interpretation: str = "medium"
    alpha: float = 0.05
    alternative: str = "two-sided"
    ratio: float = 1.0  # n2/n1 for unequal groups
    
    # For proportion tests
    p1: Optional[float] = None
    p2: Optional[float] = None
    
    # For t-tests with raw values
    mean1: Optional[float] = None
    mean2: Optional[float] = None
    sd: Optional[float] = None
    
    # Sensitivity analysis
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    
    # Interpretation
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    method: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "test_type": self.test_type,
            "scenario": self.scenario,
            "results": {
                "sample_size_per_group": self.sample_size_per_group,
                "total_sample_size": self.total_sample_size,
                "power": safe_round(self.power, 4),
            },
            "parameters": {
                "effect_size": safe_round(self.effect_size, 4),
                "effect_size_type": self.effect_size_type,
                "effect_size_interpretation": self.effect_size_interpretation,
                "alpha": self.alpha,
                "alternative": self.alternative,
                "ratio": self.ratio,
                "p1": safe_round(self.p1, 4),
                "p2": safe_round(self.p2, 4),
                "mean1": safe_round(self.mean1, 4),
                "mean2": safe_round(self.mean2, 4),
                "sd": safe_round(self.sd, 4),
            },
            "sensitivity_analysis": self.sensitivity_analysis,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "method": self.method,
            "notes": self.notes,
        }

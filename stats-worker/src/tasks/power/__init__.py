"""
Power Analysis Package

Domain-driven modular structure for power analysis calculations.

Submodules:
    - base: Shared types, constants, and helper functions
    - ttest: T-test and proportion power analysis
    - anova: ANOVA power analysis
    - chisquare: Chi-square power analysis
    - survival: Survival analysis power
"""

from .anova import ANOVAPowerAnalysis, ANOVAPowerResult
from .base import (
    EFFECT_SIZE_THRESHOLDS,
    EffectSizeType,
    PowerAnalysisResult,
    TestType,
    cohens_d_from_means,
    cohens_h_from_proportions,
    interpret_effect_size,
    safe_round,
)
from .chisquare import ChiSquarePowerAnalysis, ChiSquarePowerResult
from .survival import SurvivalPowerAnalysis, SurvivalPowerResult
from .ttest import ProportionPowerAnalysis, TTestPowerAnalysis

__all__ = [
    # Base
    "EffectSizeType",
    "TestType",
    "EFFECT_SIZE_THRESHOLDS",
    "PowerAnalysisResult",
    "safe_round",
    "interpret_effect_size",
    "cohens_d_from_means",
    "cohens_h_from_proportions",
    # T-test
    "TTestPowerAnalysis",
    "ProportionPowerAnalysis",
    # ANOVA
    "ANOVAPowerAnalysis",
    "ANOVAPowerResult",
    # Chi-square
    "ChiSquarePowerAnalysis",
    "ChiSquarePowerResult",
    # Survival
    "SurvivalPowerAnalysis",
    "SurvivalPowerResult",
]

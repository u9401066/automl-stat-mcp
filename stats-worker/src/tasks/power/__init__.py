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
from .base import (
    EffectSizeType,
    TestType,
    EFFECT_SIZE_THRESHOLDS,
    PowerAnalysisResult,
    safe_round,
    interpret_effect_size,
    cohens_d_from_means,
    cohens_h_from_proportions,
)
from .ttest import TTestPowerAnalysis, ProportionPowerAnalysis
from .anova import ANOVAPowerAnalysis, ANOVAPowerResult
from .chisquare import ChiSquarePowerAnalysis, ChiSquarePowerResult
from .survival import SurvivalPowerAnalysis, SurvivalPowerResult

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

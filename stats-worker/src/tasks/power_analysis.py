"""
Power Analysis Module - Phase 6

Sample size and power calculations for clinical research design.

This module has been refactored into a modular DDD structure.
All functionality is re-exported from submodules for backward compatibility.

Submodules:
    - power.base: Shared types, constants, and helper functions
    - power.ttest: T-test and proportion power analysis
    - power.anova: ANOVA power analysis
    - power.chisquare: Chi-square power analysis
    - power.survival: Survival analysis power

Features:
    - T-test power analysis (two-sample, paired, one-sample)
    - Proportion test power analysis (two proportions, one proportion)
    - ANOVA power analysis (one-way F-test)
    - Chi-square power analysis (goodness-of-fit, independence)
    - Survival analysis power (log-rank test, Schoenfeld formula)
    - Effect size calculations and interpretations
    - Sensitivity analysis with power curves

Dependencies:
    - statsmodels.stats.power
    - scipy.stats
"""

# =============================================================================
# Re-export all from submodules for backward compatibility
# =============================================================================

# Base types and helpers
from .power.base import (
    EffectSizeType,
    TestType,
    EFFECT_SIZE_THRESHOLDS,
    PowerAnalysisResult,
    safe_round,
    interpret_effect_size,
    cohens_d_from_means,
    cohens_h_from_proportions,
)

# T-test and Proportion analysis
from .power.ttest import (
    TTestPowerAnalysis,
    ProportionPowerAnalysis,
    calculate_ttest_sample_size,
    calculate_ttest_power,
    calculate_proportion_sample_size,
    calculate_proportion_power,
)

# ANOVA analysis
from .power.anova import (
    ANOVAPowerResult,
    ANOVAPowerAnalysis,
    cohens_f_from_means,
    cohens_f_from_eta_squared,
    eta_squared_from_cohens_f,
    calculate_anova_sample_size,
    calculate_anova_power,
)

# Chi-square analysis
from .power.chisquare import (
    ChiSquarePowerResult,
    ChiSquarePowerAnalysis,
    cramers_v_from_table,
    effect_size_w_from_proportions,
    calculate_chisquare_sample_size,
    calculate_chisquare_power,
)

# Survival analysis
from .power.survival import (
    SurvivalPowerResult,
    SurvivalPowerAnalysis,
    hazard_ratio_to_log_hr,
    log_hr_to_hazard_ratio,
    events_from_survival,
    sample_size_from_events,
    calculate_survival_events,
    calculate_survival_sample_size,
    calculate_survival_power,
    calculate_survival_from_medians,
)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Enums and Types
    "EffectSizeType",
    "TestType",
    "EFFECT_SIZE_THRESHOLDS",
    "PowerAnalysisResult",
    "ANOVAPowerResult",
    "ChiSquarePowerResult",
    "SurvivalPowerResult",
    
    # Helper Functions
    "safe_round",
    "interpret_effect_size",
    "cohens_d_from_means",
    "cohens_h_from_proportions",
    "cohens_f_from_means",
    "cohens_f_from_eta_squared",
    "eta_squared_from_cohens_f",
    "cramers_v_from_table",
    "effect_size_w_from_proportions",
    "hazard_ratio_to_log_hr",
    "log_hr_to_hazard_ratio",
    "events_from_survival",
    "sample_size_from_events",
    
    # Analysis Classes
    "TTestPowerAnalysis",
    "ProportionPowerAnalysis",
    "ANOVAPowerAnalysis",
    "ChiSquarePowerAnalysis",
    "SurvivalPowerAnalysis",
    
    # MCP Convenience Functions - T-test
    "calculate_ttest_sample_size",
    "calculate_ttest_power",
    
    # MCP Convenience Functions - Proportion
    "calculate_proportion_sample_size",
    "calculate_proportion_power",
    
    # MCP Convenience Functions - ANOVA
    "calculate_anova_sample_size",
    "calculate_anova_power",
    
    # MCP Convenience Functions - Chi-square
    "calculate_chisquare_sample_size",
    "calculate_chisquare_power",
    
    # MCP Convenience Functions - Survival
    "calculate_survival_events",
    "calculate_survival_sample_size",
    "calculate_survival_power",
    "calculate_survival_from_medians",
]

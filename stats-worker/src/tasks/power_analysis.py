"""
Power Analysis Module - Phase 6.1

Sample size and power calculations for clinical research design.

Features:
- T-test power analysis (two-sample, paired, one-sample)
- Proportion test power analysis (two proportions, one proportion)
- Effect size calculations and interpretations
- Sensitivity analysis with power curves

Dependencies:
- statsmodels.stats.power
- scipy.stats
"""
import logging
import math
from typing import Dict, List, Any, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy import stats

# Import statsmodels power analysis tools
from statsmodels.stats.power import (
    TTestIndPower,
    TTestPower,
    NormalIndPower,
)
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
    """Round a value safely, returning None for NaN/Inf"""
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


# =============================================================================
# T-Test Power Analysis
# =============================================================================

class TTestPowerAnalysis:
    """
    Power analysis for t-tests.
    
    Supports:
    - Two-sample independent t-test
    - Paired t-test
    - One-sample t-test
    """
    
    @staticmethod
    def calculate_sample_size(
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
        ratio: float = 1.0,
        test_type: Literal["two-sample", "paired", "one-sample"] = "two-sample",
        # Alternative: specify means and SD instead of effect size
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        sd: Optional[float] = None,
    ) -> PowerAnalysisResult:
        """
        Calculate required sample size for t-test.
        
        Args:
            effect_size: Cohen's d (if not provided, calculated from means/sd)
            alpha: Significance level (default 0.05)
            power: Desired power (default 0.80)
            alternative: "two-sided", "larger", "smaller"
            ratio: Ratio of n2/n1 for unequal group sizes (default 1.0)
            test_type: "two-sample", "paired", or "one-sample"
            mean1: Mean of group 1 (alternative to effect_size)
            mean2: Mean of group 2 (alternative to effect_size)
            sd: Standard deviation (pooled or common)
            
        Returns:
            PowerAnalysisResult with sample size calculation
        """
        # Calculate effect size if not provided
        if effect_size is None:
            if mean1 is not None and mean2 is not None and sd is not None:
                effect_size = cohens_d_from_means(mean1, mean2, sd)
            else:
                raise ValueError(
                    "Either effect_size or (mean1, mean2, sd) must be provided"
                )
        
        # Ensure positive effect size for calculation
        effect_size_abs = abs(effect_size)
        
        # Validate parameters
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        if not 0 < power < 1:
            raise ValueError("power must be between 0 and 1")
        if effect_size_abs <= 0:
            raise ValueError("effect_size must be non-zero")
        if ratio <= 0:
            raise ValueError("ratio must be positive")
        
        # Select appropriate power analysis tool
        if test_type == "two-sample":
            analysis = TTestIndPower()
            n = analysis.solve_power(
                effect_size=effect_size_abs,
                alpha=alpha,
                power=power,
                ratio=ratio,
                alternative=alternative,
            )
            n1 = math.ceil(n)
            n2 = math.ceil(n * ratio)
            total_n = n1 + n2
            test_name = TestType.TTEST_IND.value
            
        elif test_type == "paired":
            analysis = TTestPower()
            n = analysis.solve_power(
                effect_size=effect_size_abs,
                alpha=alpha,
                power=power,
                alternative=alternative,
            )
            n1 = math.ceil(n)
            n2 = n1  # Paired test has same n
            total_n = n1  # Total is number of pairs
            test_name = TestType.TTEST_PAIRED.value
            
        elif test_type == "one-sample":
            analysis = TTestPower()
            n = analysis.solve_power(
                effect_size=effect_size_abs,
                alpha=alpha,
                power=power,
                alternative=alternative,
            )
            n1 = math.ceil(n)
            n2 = None
            total_n = n1
            test_name = TestType.TTEST_ONE.value
            
        else:
            raise ValueError(f"Unknown test_type: {test_type}")
        
        # Effect size interpretation
        es_interpretation = interpret_effect_size(effect_size_abs, "cohens_d")
        
        # Generate interpretation
        if test_type == "two-sample":
            interpretation = (
                f"To detect a {es_interpretation} effect (Cohen's d = {effect_size_abs:.3f}) "
                f"with {power*100:.0f}% power at α = {alpha}, "
                f"you need {n1} participants in group 1 and {n2} in group 2 "
                f"(total N = {total_n})."
            )
        elif test_type == "paired":
            interpretation = (
                f"To detect a {es_interpretation} effect (Cohen's d = {effect_size_abs:.3f}) "
                f"with {power*100:.0f}% power at α = {alpha}, "
                f"you need {n1} pairs of measurements."
            )
        else:  # one-sample
            interpretation = (
                f"To detect a {es_interpretation} effect (Cohen's d = {effect_size_abs:.3f}) "
                f"with {power*100:.0f}% power at α = {alpha}, "
                f"you need {n1} participants."
            )
        
        # Generate recommendations
        recommendations = []
        if es_interpretation == "small":
            recommendations.append(
                "Small effect sizes require large samples. "
                "Consider whether this effect is clinically meaningful."
            )
        if power < 0.80:
            recommendations.append(
                "Power < 80% may result in false negatives. "
                "Consider increasing sample size if feasible."
            )
        if total_n > 500:
            recommendations.append(
                "Large sample requirement. Consider pilot study first "
                "to verify effect size estimate."
            )
        
        # Sensitivity analysis
        sensitivity = TTestPowerAnalysis._sensitivity_analysis(
            effect_size=effect_size_abs,
            alpha=alpha,
            power=power,
            test_type=test_type,
            ratio=ratio,
            alternative=alternative,
        )
        
        return PowerAnalysisResult(
            test_type=test_name,
            scenario="sample_size",
            sample_size_per_group=n1,
            total_sample_size=total_n,
            power=power,
            effect_size=effect_size,
            effect_size_type=EffectSizeType.COHENS_D.value,
            effect_size_interpretation=es_interpretation,
            alpha=alpha,
            alternative=alternative,
            ratio=ratio,
            mean1=mean1,
            mean2=mean2,
            sd=sd,
            sensitivity_analysis=sensitivity,
            interpretation=interpretation,
            recommendations=recommendations,
            method="statsmodels TTestIndPower/TTestPower",
        )
    
    @staticmethod
    def calculate_power(
        n: int,
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
        ratio: float = 1.0,
        test_type: Literal["two-sample", "paired", "one-sample"] = "two-sample",
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        sd: Optional[float] = None,
    ) -> PowerAnalysisResult:
        """
        Calculate power given sample size.
        
        Args:
            n: Sample size (per group for two-sample, total pairs for paired)
            effect_size: Cohen's d
            alpha: Significance level
            alternative: "two-sided", "larger", "smaller"
            ratio: Ratio of n2/n1
            test_type: "two-sample", "paired", or "one-sample"
            mean1, mean2, sd: Alternative to effect_size
            
        Returns:
            PowerAnalysisResult with power calculation
        """
        # Calculate effect size if not provided
        if effect_size is None:
            if mean1 is not None and mean2 is not None and sd is not None:
                effect_size = cohens_d_from_means(mean1, mean2, sd)
            else:
                raise ValueError(
                    "Either effect_size or (mean1, mean2, sd) must be provided"
                )
        
        effect_size_abs = abs(effect_size)
        
        # Select appropriate power analysis tool
        if test_type == "two-sample":
            analysis = TTestIndPower()
            power = analysis.solve_power(
                effect_size=effect_size_abs,
                nobs1=n,
                alpha=alpha,
                ratio=ratio,
                alternative=alternative,
            )
            n2 = math.ceil(n * ratio)
            total_n = n + n2
            test_name = TestType.TTEST_IND.value
            
        elif test_type == "paired":
            analysis = TTestPower()
            power = analysis.solve_power(
                effect_size=effect_size_abs,
                nobs=n,
                alpha=alpha,
                alternative=alternative,
            )
            n2 = n
            total_n = n
            test_name = TestType.TTEST_PAIRED.value
            
        else:  # one-sample
            analysis = TTestPower()
            power = analysis.solve_power(
                effect_size=effect_size_abs,
                nobs=n,
                alpha=alpha,
                alternative=alternative,
            )
            n2 = None
            total_n = n
            test_name = TestType.TTEST_ONE.value
        
        es_interpretation = interpret_effect_size(effect_size_abs, "cohens_d")
        
        interpretation = (
            f"With n = {n} {'per group' if test_type == 'two-sample' else ''}, "
            f"effect size d = {effect_size_abs:.3f} ({es_interpretation}), "
            f"and α = {alpha}, the study has {power*100:.1f}% power."
        )
        
        recommendations = []
        if power < 0.80:
            recommendations.append(
                f"Power is below 80%. Consider increasing sample size to achieve adequate power."
            )
        if power > 0.95:
            recommendations.append(
                "Power > 95% may indicate over-sampling. "
                "Resources could be optimized with fewer participants."
            )
        
        return PowerAnalysisResult(
            test_type=test_name,
            scenario="power",
            sample_size_per_group=n,
            total_sample_size=total_n,
            power=power,
            effect_size=effect_size,
            effect_size_type=EffectSizeType.COHENS_D.value,
            effect_size_interpretation=es_interpretation,
            alpha=alpha,
            alternative=alternative,
            ratio=ratio,
            mean1=mean1,
            mean2=mean2,
            sd=sd,
            interpretation=interpretation,
            recommendations=recommendations,
            method="statsmodels TTestIndPower/TTestPower",
        )
    
    @staticmethod
    def _sensitivity_analysis(
        effect_size: float,
        alpha: float,
        power: float,
        test_type: str,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis data for power curves"""
        
        if test_type == "two-sample":
            analysis = TTestIndPower()
        else:
            analysis = TTestPower()
        
        # Power curve: varying effect size
        effect_sizes = np.linspace(0.1, 1.0, 10)
        sample_sizes_by_es = []
        for es in effect_sizes:
            try:
                if test_type == "two-sample":
                    n = analysis.solve_power(
                        effect_size=es,
                        alpha=alpha,
                        power=power,
                        ratio=ratio,
                        alternative=alternative,
                    )
                else:
                    n = analysis.solve_power(
                        effect_size=es,
                        alpha=alpha,
                        power=power,
                        alternative=alternative,
                    )
                sample_sizes_by_es.append({"effect_size": round(es, 2), "n": math.ceil(n)})
            except Exception:
                sample_sizes_by_es.append({"effect_size": round(es, 2), "n": None})
        
        # Power curve: varying power levels
        power_levels = [0.70, 0.80, 0.85, 0.90, 0.95]
        sample_sizes_by_power = []
        for pwr in power_levels:
            try:
                if test_type == "two-sample":
                    n = analysis.solve_power(
                        effect_size=effect_size,
                        alpha=alpha,
                        power=pwr,
                        ratio=ratio,
                        alternative=alternative,
                    )
                else:
                    n = analysis.solve_power(
                        effect_size=effect_size,
                        alpha=alpha,
                        power=pwr,
                        alternative=alternative,
                    )
                sample_sizes_by_power.append({"power": pwr, "n": math.ceil(n)})
            except Exception:
                sample_sizes_by_power.append({"power": pwr, "n": None})
        
        return {
            "by_effect_size": sample_sizes_by_es,
            "by_power_level": sample_sizes_by_power,
        }


# =============================================================================
# Proportion Test Power Analysis
# =============================================================================

class ProportionPowerAnalysis:
    """
    Power analysis for proportion tests.
    
    Supports:
    - Two independent proportions (chi-square test)
    - One proportion vs hypothesized value
    """
    
    @staticmethod
    def calculate_sample_size(
        p1: float,
        p2: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
        ratio: float = 1.0,
        test_type: Literal["two-sample", "one-sample"] = "two-sample",
        p0: Optional[float] = None,  # For one-sample test
    ) -> PowerAnalysisResult:
        """
        Calculate required sample size for proportion test.
        
        Args:
            p1: Proportion in group 1 (or observed proportion for one-sample)
            p2: Proportion in group 2 (for two-sample test)
            alpha: Significance level
            power: Desired power
            alternative: "two-sided", "larger", "smaller"
            ratio: Ratio of n2/n1 for unequal groups
            test_type: "two-sample" or "one-sample"
            p0: Hypothesized proportion (for one-sample test)
            
        Returns:
            PowerAnalysisResult with sample size calculation
        """
        # Validate proportions
        if not 0 < p1 < 1:
            raise ValueError("p1 must be between 0 and 1")
        
        if test_type == "two-sample":
            if p2 is None:
                raise ValueError("p2 is required for two-sample test")
            if not 0 < p2 < 1:
                raise ValueError("p2 must be between 0 and 1")
            
            # Calculate Cohen's h
            effect_size = cohens_h_from_proportions(p1, p2)
            effect_size_abs = abs(effect_size)
            
            # Use NormalIndPower for proportion test
            analysis = NormalIndPower()
            n = analysis.solve_power(
                effect_size=effect_size_abs,
                alpha=alpha,
                power=power,
                ratio=ratio,
                alternative=alternative,
            )
            
            n1 = math.ceil(n)
            n2 = math.ceil(n * ratio)
            total_n = n1 + n2
            test_name = TestType.PROPORTION_TWO.value
            
            interpretation = (
                f"To detect a difference between proportions "
                f"({p1*100:.1f}% vs {p2*100:.1f}%, Cohen's h = {effect_size_abs:.3f}) "
                f"with {power*100:.0f}% power at α = {alpha}, "
                f"you need {n1} in group 1 and {n2} in group 2 (total N = {total_n})."
            )
            
        else:  # one-sample
            if p0 is None:
                raise ValueError("p0 (hypothesized proportion) is required for one-sample test")
            if not 0 < p0 < 1:
                raise ValueError("p0 must be between 0 and 1")
            
            # Calculate Cohen's h for one-sample
            effect_size = cohens_h_from_proportions(p1, p0)
            effect_size_abs = abs(effect_size)
            
            analysis = NormalIndPower()
            # For one-sample, we use the same approach but interpret differently
            n = analysis.solve_power(
                effect_size=effect_size_abs,
                alpha=alpha,
                power=power,
                ratio=1.0,
                alternative=alternative,
            )
            
            n1 = math.ceil(n)
            n2 = None
            total_n = n1
            test_name = TestType.PROPORTION_ONE.value
            
            interpretation = (
                f"To detect a difference from hypothesized proportion "
                f"({p1*100:.1f}% vs {p0*100:.1f}%, Cohen's h = {effect_size_abs:.3f}) "
                f"with {power*100:.0f}% power at α = {alpha}, "
                f"you need {n1} participants."
            )
        
        es_interpretation = interpret_effect_size(effect_size_abs, "cohens_h")
        
        # Recommendations
        recommendations = []
        
        # Check if proportions are close to 0 or 1 (may need more samples)
        if min(p1, p2 if p2 else p1) < 0.05 or max(p1, p2 if p2 else p1) > 0.95:
            recommendations.append(
                "Extreme proportions (close to 0% or 100%) may require "
                "larger samples for stable estimates. Consider exact methods."
            )
        
        # Absolute risk difference
        if test_type == "two-sample" and p2:
            ard = abs(p1 - p2)
            nnt = 1 / ard if ard > 0 else float('inf')
            recommendations.append(
                f"Absolute risk difference: {ard*100:.1f}%. "
                f"Number needed to treat (NNT): {nnt:.1f}."
            )
        
        if es_interpretation == "small":
            recommendations.append(
                "Small effect size requires large sample. "
                "Verify if this difference is clinically meaningful."
            )
        
        # Sensitivity analysis
        sensitivity = ProportionPowerAnalysis._sensitivity_analysis(
            p1=p1, p2=p2, p0=p0,
            alpha=alpha, power=power,
            test_type=test_type, ratio=ratio,
            alternative=alternative,
        )
        
        return PowerAnalysisResult(
            test_type=test_name,
            scenario="sample_size",
            sample_size_per_group=n1,
            total_sample_size=total_n,
            power=power,
            effect_size=effect_size,
            effect_size_type=EffectSizeType.COHENS_H.value,
            effect_size_interpretation=es_interpretation,
            alpha=alpha,
            alternative=alternative,
            ratio=ratio,
            p1=p1,
            p2=p2 if test_type == "two-sample" else p0,
            sensitivity_analysis=sensitivity,
            interpretation=interpretation,
            recommendations=recommendations,
            method="statsmodels NormalIndPower (normal approximation)",
            notes=["Uses arcsine transformation (Cohen's h) for effect size"],
        )
    
    @staticmethod
    def calculate_power(
        n: int,
        p1: float,
        p2: Optional[float] = None,
        alpha: float = 0.05,
        alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
        ratio: float = 1.0,
        test_type: Literal["two-sample", "one-sample"] = "two-sample",
        p0: Optional[float] = None,
    ) -> PowerAnalysisResult:
        """
        Calculate power given sample size for proportion test.
        
        Args:
            n: Sample size per group (for two-sample) or total (for one-sample)
            p1: Proportion in group 1
            p2: Proportion in group 2 (for two-sample)
            alpha: Significance level
            alternative: "two-sided", "larger", "smaller"
            ratio: Ratio of n2/n1
            test_type: "two-sample" or "one-sample"
            p0: Hypothesized proportion (for one-sample)
            
        Returns:
            PowerAnalysisResult with power calculation
        """
        if test_type == "two-sample":
            if p2 is None:
                raise ValueError("p2 is required for two-sample test")
            effect_size = cohens_h_from_proportions(p1, p2)
            test_name = TestType.PROPORTION_TWO.value
            n2 = math.ceil(n * ratio)
            total_n = n + n2
        else:
            if p0 is None:
                raise ValueError("p0 is required for one-sample test")
            effect_size = cohens_h_from_proportions(p1, p0)
            test_name = TestType.PROPORTION_ONE.value
            n2 = None
            total_n = n
        
        effect_size_abs = abs(effect_size)
        
        analysis = NormalIndPower()
        power = analysis.solve_power(
            effect_size=effect_size_abs,
            nobs1=n,
            alpha=alpha,
            ratio=ratio if test_type == "two-sample" else 1.0,
            alternative=alternative,
        )
        
        es_interpretation = interpret_effect_size(effect_size_abs, "cohens_h")
        
        if test_type == "two-sample":
            interpretation = (
                f"With n = {n} per group, comparing {p1*100:.1f}% vs {p2*100:.1f}% "
                f"(Cohen's h = {effect_size_abs:.3f}), "
                f"the study has {power*100:.1f}% power at α = {alpha}."
            )
        else:
            interpretation = (
                f"With n = {n}, comparing {p1*100:.1f}% vs hypothesized {p0*100:.1f}% "
                f"(Cohen's h = {effect_size_abs:.3f}), "
                f"the study has {power*100:.1f}% power at α = {alpha}."
            )
        
        recommendations = []
        if power < 0.80:
            recommendations.append(
                f"Power is {power*100:.1f}%, below the recommended 80%. "
                "Consider increasing sample size."
            )
        
        return PowerAnalysisResult(
            test_type=test_name,
            scenario="power",
            sample_size_per_group=n,
            total_sample_size=total_n,
            power=power,
            effect_size=effect_size,
            effect_size_type=EffectSizeType.COHENS_H.value,
            effect_size_interpretation=es_interpretation,
            alpha=alpha,
            alternative=alternative,
            ratio=ratio,
            p1=p1,
            p2=p2 if test_type == "two-sample" else p0,
            interpretation=interpretation,
            recommendations=recommendations,
            method="statsmodels NormalIndPower",
        )
    
    @staticmethod
    def _sensitivity_analysis(
        p1: float,
        p2: Optional[float],
        p0: Optional[float],
        alpha: float,
        power: float,
        test_type: str,
        ratio: float,
        alternative: str,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for proportion tests"""
        
        analysis = NormalIndPower()
        
        # Sample size at different power levels
        power_levels = [0.70, 0.80, 0.85, 0.90, 0.95]
        base_es = abs(cohens_h_from_proportions(p1, p2 if p2 else p0))
        
        sample_sizes_by_power = []
        for pwr in power_levels:
            try:
                n = analysis.solve_power(
                    effect_size=base_es,
                    alpha=alpha,
                    power=pwr,
                    ratio=ratio if test_type == "two-sample" else 1.0,
                    alternative=alternative,
                )
                sample_sizes_by_power.append({"power": pwr, "n": math.ceil(n)})
            except Exception:
                sample_sizes_by_power.append({"power": pwr, "n": None})
        
        # For two-sample: vary p2 while keeping p1 fixed
        if test_type == "two-sample" and p2:
            p2_variations = []
            base_diff = p2 - p1
            for delta in [-0.10, -0.05, 0, 0.05, 0.10]:
                new_p2 = max(0.01, min(0.99, p2 + delta))
                es = abs(cohens_h_from_proportions(p1, new_p2))
                try:
                    n = analysis.solve_power(
                        effect_size=es,
                        alpha=alpha,
                        power=power,
                        ratio=ratio,
                        alternative=alternative,
                    )
                    p2_variations.append({
                        "p2": round(new_p2, 3),
                        "effect_size": round(es, 3),
                        "n": math.ceil(n)
                    })
                except Exception:
                    pass
            
            return {
                "by_power_level": sample_sizes_by_power,
                "by_p2_variation": p2_variations,
            }
        
        return {
            "by_power_level": sample_sizes_by_power,
        }


# =============================================================================
# Convenience Functions (for MCP tools)
# =============================================================================

def calculate_ttest_sample_size(
    effect_size: Optional[float] = None,
    mean1: Optional[float] = None,
    mean2: Optional[float] = None,
    sd: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: str = "two-sided",
    ratio: float = 1.0,
    test_type: str = "two-sample",
) -> Dict[str, Any]:
    """
    Calculate sample size for t-test (MCP-friendly wrapper).
    
    Args:
        effect_size: Cohen's d effect size
        mean1: Mean of group 1 (alternative to effect_size)
        mean2: Mean of group 2 (alternative to effect_size)
        sd: Pooled standard deviation (alternative to effect_size)
        alpha: Significance level (default 0.05)
        power: Desired power (default 0.80)
        alternative: "two-sided", "larger", "smaller"
        ratio: n2/n1 ratio for unequal groups
        test_type: "two-sample", "paired", "one-sample"
        
    Returns:
        Dictionary with sample size calculation results
    """
    result = TTestPowerAnalysis.calculate_sample_size(
        effect_size=effect_size,
        mean1=mean1,
        mean2=mean2,
        sd=sd,
        alpha=alpha,
        power=power,
        alternative=alternative,
        ratio=ratio,
        test_type=test_type,
    )
    return result.to_dict()


def calculate_ttest_power(
    n: int,
    effect_size: Optional[float] = None,
    mean1: Optional[float] = None,
    mean2: Optional[float] = None,
    sd: Optional[float] = None,
    alpha: float = 0.05,
    alternative: str = "two-sided",
    ratio: float = 1.0,
    test_type: str = "two-sample",
) -> Dict[str, Any]:
    """
    Calculate power for t-test given sample size (MCP-friendly wrapper).
    
    Args:
        n: Sample size (per group for two-sample)
        effect_size: Cohen's d effect size
        mean1, mean2, sd: Alternative to effect_size
        alpha: Significance level
        alternative: "two-sided", "larger", "smaller"
        ratio: n2/n1 ratio
        test_type: "two-sample", "paired", "one-sample"
        
    Returns:
        Dictionary with power calculation results
    """
    result = TTestPowerAnalysis.calculate_power(
        n=n,
        effect_size=effect_size,
        mean1=mean1,
        mean2=mean2,
        sd=sd,
        alpha=alpha,
        alternative=alternative,
        ratio=ratio,
        test_type=test_type,
    )
    return result.to_dict()


def calculate_proportion_sample_size(
    p1: float,
    p2: Optional[float] = None,
    p0: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: str = "two-sided",
    ratio: float = 1.0,
    test_type: str = "two-sample",
) -> Dict[str, Any]:
    """
    Calculate sample size for proportion test (MCP-friendly wrapper).
    
    Args:
        p1: Proportion in group 1
        p2: Proportion in group 2 (for two-sample test)
        p0: Hypothesized proportion (for one-sample test)
        alpha: Significance level
        power: Desired power
        alternative: "two-sided", "larger", "smaller"
        ratio: n2/n1 ratio
        test_type: "two-sample" or "one-sample"
        
    Returns:
        Dictionary with sample size calculation results
    """
    result = ProportionPowerAnalysis.calculate_sample_size(
        p1=p1,
        p2=p2,
        p0=p0,
        alpha=alpha,
        power=power,
        alternative=alternative,
        ratio=ratio,
        test_type=test_type,
    )
    return result.to_dict()


def calculate_proportion_power(
    n: int,
    p1: float,
    p2: Optional[float] = None,
    p0: Optional[float] = None,
    alpha: float = 0.05,
    alternative: str = "two-sided",
    ratio: float = 1.0,
    test_type: str = "two-sample",
) -> Dict[str, Any]:
    """
    Calculate power for proportion test given sample size (MCP-friendly wrapper).
    
    Args:
        n: Sample size per group
        p1: Proportion in group 1
        p2: Proportion in group 2 (for two-sample)
        p0: Hypothesized proportion (for one-sample)
        alpha: Significance level
        alternative: "two-sided", "larger", "smaller"
        ratio: n2/n1 ratio
        test_type: "two-sample" or "one-sample"
        
    Returns:
        Dictionary with power calculation results
    """
    result = ProportionPowerAnalysis.calculate_power(
        n=n,
        p1=p1,
        p2=p2,
        p0=p0,
        alpha=alpha,
        alternative=alternative,
        ratio=ratio,
        test_type=test_type,
    )
    return result.to_dict()


# =============================================================================
# Phase 6.2: ANOVA Power Analysis
# =============================================================================

# Import additional statsmodels for ANOVA
from statsmodels.stats.power import FTestAnovaPower


def cohens_f_from_means(
    group_means: List[float],
    group_sds: Optional[List[float]] = None,
    pooled_sd: Optional[float] = None,
) -> float:
    """
    Calculate Cohen's f from group means.
    
    Cohen's f = sqrt(sum((μi - μ)²) / k) / σ
    
    Args:
        group_means: List of group means
        group_sds: List of group standard deviations (optional)
        pooled_sd: Pooled standard deviation (if known)
        
    Returns:
        Cohen's f effect size
    """
    if len(group_means) < 2:
        raise ValueError("Need at least 2 groups for ANOVA")
    
    grand_mean = np.mean(group_means)
    k = len(group_means)
    
    # Calculate between-group variance
    between_var = np.sum([(m - grand_mean)**2 for m in group_means]) / k
    
    # Estimate pooled SD if not provided
    if pooled_sd is None:
        if group_sds is not None and len(group_sds) == len(group_means):
            pooled_sd = np.sqrt(np.mean([s**2 for s in group_sds]))
        else:
            raise ValueError("Need either pooled_sd or group_sds")
    
    if pooled_sd == 0:
        return 0.0
    
    return math.sqrt(between_var) / pooled_sd


def cohens_f_from_eta_squared(eta_squared: float) -> float:
    """
    Convert eta-squared (η²) to Cohen's f.
    
    f = sqrt(η² / (1 - η²))
    
    Args:
        eta_squared: Eta-squared effect size (0-1)
        
    Returns:
        Cohen's f effect size
    """
    if eta_squared < 0 or eta_squared >= 1:
        raise ValueError("eta_squared must be between 0 and 1 (exclusive)")
    
    return math.sqrt(eta_squared / (1 - eta_squared))


def eta_squared_from_cohens_f(cohens_f: float) -> float:
    """
    Convert Cohen's f to eta-squared (η²).
    
    η² = f² / (1 + f²)
    
    Args:
        cohens_f: Cohen's f effect size
        
    Returns:
        Eta-squared effect size
    """
    f_squared = cohens_f ** 2
    return f_squared / (1 + f_squared)


@dataclass
class ANOVAPowerResult:
    """Result of ANOVA power analysis"""
    
    test_type: str = "one-way ANOVA"
    scenario: str = "sample_size"  # or "power"
    
    # Main results
    n_per_group: Optional[int] = None
    total_n: Optional[int] = None
    power: Optional[float] = None
    
    # Parameters
    k_groups: int = 2  # Number of groups
    effect_size_f: Optional[float] = None
    eta_squared: Optional[float] = None
    effect_size_interpretation: str = "medium"
    alpha: float = 0.05
    
    # Optional: from raw means
    group_means: Optional[List[float]] = None
    pooled_sd: Optional[float] = None
    
    # Sensitivity
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    
    # Interpretation
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    method: str = "statsmodels FTestAnovaPower"
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_type": self.test_type,
            "scenario": self.scenario,
            "results": {
                "n_per_group": self.n_per_group,
                "total_n": self.total_n,
                "power": safe_round(self.power, 4),
            },
            "parameters": {
                "k_groups": self.k_groups,
                "effect_size_f": safe_round(self.effect_size_f, 4),
                "eta_squared": safe_round(self.eta_squared, 4),
                "effect_size_interpretation": self.effect_size_interpretation,
                "alpha": self.alpha,
                "group_means": self.group_means,
                "pooled_sd": safe_round(self.pooled_sd, 4),
            },
            "sensitivity_analysis": self.sensitivity_analysis,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "method": self.method,
            "notes": self.notes,
        }


class ANOVAPowerAnalysis:
    """
    Power analysis for one-way ANOVA (F-test).
    
    Supports:
    - Sample size calculation given effect size and power
    - Power calculation given sample size
    - Effect size from group means or eta-squared
    - Sensitivity analysis
    
    Effect size conventions (Cohen's f):
    - Small: 0.10
    - Medium: 0.25
    - Large: 0.40
    """
    
    @staticmethod
    def calculate_sample_size(
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        power: float = 0.80,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> ANOVAPowerResult:
        """
        Calculate sample size per group for one-way ANOVA.
        
        Args:
            effect_size: Cohen's f (if not provided, calculated from other params)
            k_groups: Number of groups
            alpha: Significance level
            power: Desired power (0-1)
            group_means: Group means to calculate effect size
            pooled_sd: Pooled standard deviation
            eta_squared: Eta-squared to convert to Cohen's f
            
        Returns:
            ANOVAPowerResult with sample size requirements
        """
        # Validate parameters
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        if not 0 < power < 1:
            raise ValueError("power must be between 0 and 1")
        if k_groups < 2:
            raise ValueError("Need at least 2 groups for ANOVA")
        
        # Calculate effect size if not provided
        if effect_size is None:
            if eta_squared is not None:
                effect_size = cohens_f_from_eta_squared(eta_squared)
            elif group_means is not None and pooled_sd is not None:
                effect_size = cohens_f_from_means(group_means, pooled_sd=pooled_sd)
                k_groups = len(group_means)
            else:
                raise ValueError(
                    "Provide effect_size (Cohen's f), eta_squared, or (group_means + pooled_sd)"
                )
        
        # Calculate sample size using statsmodels
        anova_power = FTestAnovaPower()
        
        # df_num = k - 1 (between groups)
        # df_denom = N - k (within groups), but we solve for n
        n_per_group = anova_power.solve_power(
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            k_groups=k_groups,
        )
        
        n_per_group = int(math.ceil(n_per_group))
        total_n = n_per_group * k_groups
        
        # Effect size interpretation
        interpretation_str = interpret_effect_size(effect_size, "cohens_f")
        
        # Calculate eta-squared
        eta_sq = eta_squared_from_cohens_f(effect_size)
        
        # Sensitivity analysis
        sensitivity = ANOVAPowerAnalysis._sensitivity_analysis(
            effect_size=effect_size,
            k_groups=k_groups,
            alpha=alpha,
        )
        
        # Generate interpretation
        interp_text = (
            f"To detect an effect (Cohen's f = {effect_size:.3f}, η² = {eta_sq:.3f}) "
            f"with {power*100:.0f}% power at α = {alpha} across {k_groups} groups, "
            f"you need {n_per_group} per group (total N = {total_n})."
        )
        
        # Recommendations
        recs = []
        if interpretation_str == "small":
            recs.append("Small effect size requires large sample. Verify clinical significance.")
        if n_per_group < 20:
            recs.append("Sample size is small. Consider if ANOVA assumptions will hold.")
        if k_groups > 5:
            recs.append(f"With {k_groups} groups, consider planned contrasts for specific comparisons.")
        recs.append(f"Eta-squared ({eta_sq:.3f}) indicates {eta_sq*100:.1f}% of variance explained by group.")
        
        return ANOVAPowerResult(
            test_type="one-way ANOVA",
            scenario="sample_size",
            n_per_group=n_per_group,
            total_n=total_n,
            power=power,
            k_groups=k_groups,
            effect_size_f=effect_size,
            eta_squared=eta_sq,
            effect_size_interpretation=interpretation_str,
            alpha=alpha,
            group_means=group_means,
            pooled_sd=pooled_sd,
            sensitivity_analysis=sensitivity,
            interpretation=interp_text,
            recommendations=recs,
        )
    
    @staticmethod
    def calculate_power(
        n_per_group: int,
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> ANOVAPowerResult:
        """
        Calculate power for ANOVA given sample size.
        
        Args:
            n_per_group: Sample size per group
            effect_size: Cohen's f
            k_groups: Number of groups
            alpha: Significance level
            group_means: Group means to calculate effect size
            pooled_sd: Pooled standard deviation
            eta_squared: Eta-squared to convert
            
        Returns:
            ANOVAPowerResult with power calculation
        """
        # Calculate effect size if needed
        if effect_size is None:
            if eta_squared is not None:
                effect_size = cohens_f_from_eta_squared(eta_squared)
            elif group_means is not None and pooled_sd is not None:
                effect_size = cohens_f_from_means(group_means, pooled_sd=pooled_sd)
                k_groups = len(group_means)
            else:
                raise ValueError(
                    "Provide effect_size (Cohen's f), eta_squared, or (group_means + pooled_sd)"
                )
        
        # Calculate power
        anova_power = FTestAnovaPower()
        power = anova_power.solve_power(
            effect_size=effect_size,
            nobs=n_per_group,
            alpha=alpha,
            k_groups=k_groups,
            power=None,
        )
        
        # Interpretation
        interpretation_str = interpret_effect_size(effect_size, "cohens_f")
        eta_sq = eta_squared_from_cohens_f(effect_size)
        
        interp_text = (
            f"With n = {n_per_group} per group ({k_groups} groups, total N = {n_per_group * k_groups}), "
            f"effect size f = {effect_size:.3f} (η² = {eta_sq:.3f}), "
            f"the study has {power*100:.1f}% power at α = {alpha}."
        )
        
        recs = []
        if power < 0.80:
            needed_n = ANOVAPowerAnalysis.calculate_sample_size(
                effect_size=effect_size,
                k_groups=k_groups,
                alpha=alpha,
                power=0.80,
            ).n_per_group
            recs.append(f"Power is {power*100:.1f}%, below recommended 80%. Need n = {needed_n} per group for 80% power.")
        
        return ANOVAPowerResult(
            test_type="one-way ANOVA",
            scenario="power",
            n_per_group=n_per_group,
            total_n=n_per_group * k_groups,
            power=power,
            k_groups=k_groups,
            effect_size_f=effect_size,
            eta_squared=eta_sq,
            effect_size_interpretation=interpretation_str,
            alpha=alpha,
            group_means=group_means,
            pooled_sd=pooled_sd,
            interpretation=interp_text,
            recommendations=recs,
        )
    
    @staticmethod
    def _sensitivity_analysis(
        effect_size: float,
        k_groups: int,
        alpha: float,
        power_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for ANOVA"""
        if power_range is None:
            power_range = [0.70, 0.80, 0.85, 0.90, 0.95]
        
        anova_power = FTestAnovaPower()
        
        # Sample size by power level
        by_power = []
        for pwr in power_range:
            n = anova_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=pwr,
                k_groups=k_groups,
            )
            by_power.append({
                "power": pwr,
                "n_per_group": int(math.ceil(n)),
                "total_n": int(math.ceil(n)) * k_groups,
            })
        
        # Power by number of groups
        by_groups = []
        for k in [2, 3, 4, 5, 6]:
            n = anova_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=0.80,
                k_groups=k,
            )
            by_groups.append({
                "k_groups": k,
                "n_per_group": int(math.ceil(n)),
                "total_n": int(math.ceil(n)) * k,
            })
        
        return {
            "by_power_level": by_power,
            "by_k_groups": by_groups,
        }


# =============================================================================
# Phase 6.2: Chi-Square Power Analysis
# =============================================================================

from statsmodels.stats.power import GofChisquarePower


def cramers_v_from_table(observed: np.ndarray) -> float:
    """
    Calculate Cramér's V from a contingency table.
    
    Cramér's V = sqrt(χ² / (n * min(r-1, c-1)))
    
    Args:
        observed: Contingency table (2D array)
        
    Returns:
        Cramér's V effect size
    """
    chi2, p, dof, expected = stats.chi2_contingency(observed)
    n = np.sum(observed)
    min_dim = min(observed.shape) - 1
    
    if n * min_dim == 0:
        return 0.0
    
    return math.sqrt(chi2 / (n * min_dim))


def effect_size_w_from_proportions(
    p_observed: List[float],
    p_expected: Optional[List[float]] = None,
) -> float:
    """
    Calculate Cohen's w effect size for chi-square test.
    
    w = sqrt(sum((p_obs - p_exp)² / p_exp))
    
    Args:
        p_observed: Observed proportions
        p_expected: Expected proportions (uniform if None)
        
    Returns:
        Cohen's w effect size
    """
    p_obs = np.array(p_observed)
    
    if p_expected is None:
        # Uniform distribution
        k = len(p_obs)
        p_exp = np.ones(k) / k
    else:
        p_exp = np.array(p_expected)
    
    # Normalize to sum to 1
    p_obs = p_obs / np.sum(p_obs)
    p_exp = p_exp / np.sum(p_exp)
    
    # Avoid division by zero
    p_exp = np.maximum(p_exp, 1e-10)
    
    w = math.sqrt(np.sum((p_obs - p_exp)**2 / p_exp))
    return w


@dataclass
class ChiSquarePowerResult:
    """Result of chi-square power analysis"""
    
    test_type: str = "chi-square goodness-of-fit"
    scenario: str = "sample_size"
    
    # Results
    n: Optional[int] = None
    power: Optional[float] = None
    
    # Parameters
    effect_size_w: Optional[float] = None
    df: int = 1  # degrees of freedom
    alpha: float = 0.05
    n_bins: Optional[int] = None  # for goodness-of-fit
    
    # For contingency table
    n_rows: Optional[int] = None
    n_cols: Optional[int] = None
    cramers_v: Optional[float] = None
    
    # Interpretation
    effect_size_interpretation: str = "medium"
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    method: str = "statsmodels GofChisquarePower"
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_type": self.test_type,
            "scenario": self.scenario,
            "results": {
                "n": self.n,
                "power": safe_round(self.power, 4),
            },
            "parameters": {
                "effect_size_w": safe_round(self.effect_size_w, 4),
                "cramers_v": safe_round(self.cramers_v, 4),
                "df": self.df,
                "alpha": self.alpha,
                "n_bins": self.n_bins,
                "n_rows": self.n_rows,
                "n_cols": self.n_cols,
            },
            "effect_size_interpretation": self.effect_size_interpretation,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "sensitivity_analysis": self.sensitivity_analysis,
            "method": self.method,
            "notes": self.notes,
        }


class ChiSquarePowerAnalysis:
    """
    Power analysis for chi-square tests.
    
    Supports:
    - Goodness-of-fit test (one variable)
    - Test of independence (contingency table)
    
    Effect size conventions (Cohen's w):
    - Small: 0.10
    - Medium: 0.30
    - Large: 0.50
    
    Note: Cohen's w is related to Cramér's V by:
    w = V * sqrt(min(r-1, c-1)) for contingency tables
    """
    
    @staticmethod
    def calculate_sample_size(
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
        p_observed: Optional[List[float]] = None,
        p_expected: Optional[List[float]] = None,
    ) -> ChiSquarePowerResult:
        """
        Calculate sample size for chi-square test.
        
        Args:
            effect_size: Cohen's w effect size
            alpha: Significance level
            power: Desired power
            df: Degrees of freedom (calculated if not provided)
            n_bins: Number of categories for goodness-of-fit
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
            p_observed: Observed proportions (to calculate w)
            p_expected: Expected proportions
            
        Returns:
            ChiSquarePowerResult with sample size
        """
        # Determine test type and df
        test_type = "chi-square goodness-of-fit"
        
        if n_rows is not None and n_cols is not None:
            test_type = "chi-square independence"
            if df is None:
                df = (n_rows - 1) * (n_cols - 1)
        elif n_bins is not None:
            if df is None:
                df = n_bins - 1
        elif df is None:
            df = 1  # Default
        
        # Calculate effect size if not provided
        if effect_size is None:
            if p_observed is not None:
                effect_size = effect_size_w_from_proportions(p_observed, p_expected)
                if n_bins is None:
                    n_bins = len(p_observed)
                if df is None:
                    df = n_bins - 1
            else:
                raise ValueError(
                    "Provide effect_size (Cohen's w) or p_observed proportions"
                )
        
        # Calculate sample size
        chi2_power = GofChisquarePower()
        n = chi2_power.solve_power(
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            n_bins=df + 1,  # GofChisquarePower uses n_bins
        )
        
        n = int(math.ceil(n))
        
        # Effect size interpretation (same as Cohen's d convention roughly)
        if effect_size < 0.1:
            interp = "negligible"
        elif effect_size < 0.3:
            interp = "small"
        elif effect_size < 0.5:
            interp = "medium"
        else:
            interp = "large"
        
        # Cramér's V for contingency tables
        cramers_v = None
        if n_rows is not None and n_cols is not None:
            min_dim = min(n_rows - 1, n_cols - 1)
            if min_dim > 0:
                cramers_v = effect_size / math.sqrt(min_dim)
        
        # Sensitivity analysis
        sensitivity = ChiSquarePowerAnalysis._sensitivity_analysis(
            effect_size=effect_size,
            df=df,
            alpha=alpha,
        )
        
        # Interpretation
        interp_text = (
            f"To detect an effect (Cohen's w = {effect_size:.3f}) with "
            f"{power*100:.0f}% power at α = {alpha} (df = {df}), "
            f"you need N = {n}."
        )
        
        recs = []
        if interp == "small":
            recs.append("Small effect size requires large sample. Ensure effect is meaningful.")
        if df > 10:
            recs.append(f"With df = {df}, consider collapsing categories if possible.")
        if cramers_v is not None:
            recs.append(f"Cramér's V ≈ {cramers_v:.3f} for effect interpretation in contingency table.")
        
        return ChiSquarePowerResult(
            test_type=test_type,
            scenario="sample_size",
            n=n,
            power=power,
            effect_size_w=effect_size,
            df=df,
            alpha=alpha,
            n_bins=n_bins,
            n_rows=n_rows,
            n_cols=n_cols,
            cramers_v=cramers_v,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
            sensitivity_analysis=sensitivity,
        )
    
    @staticmethod
    def calculate_power(
        n: int,
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
        p_observed: Optional[List[float]] = None,
        p_expected: Optional[List[float]] = None,
    ) -> ChiSquarePowerResult:
        """
        Calculate power for chi-square test given sample size.
        
        Args:
            n: Sample size
            effect_size: Cohen's w
            alpha: Significance level
            df: Degrees of freedom
            n_bins: Number of categories
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
            p_observed: Observed proportions
            p_expected: Expected proportions
            
        Returns:
            ChiSquarePowerResult with power
        """
        # Determine test type and df
        test_type = "chi-square goodness-of-fit"
        
        if n_rows is not None and n_cols is not None:
            test_type = "chi-square independence"
            if df is None:
                df = (n_rows - 1) * (n_cols - 1)
        elif n_bins is not None:
            if df is None:
                df = n_bins - 1
        elif df is None:
            df = 1
        
        # Calculate effect size if needed
        if effect_size is None:
            if p_observed is not None:
                effect_size = effect_size_w_from_proportions(p_observed, p_expected)
                if n_bins is None:
                    n_bins = len(p_observed)
                if df is None:
                    df = n_bins - 1
            else:
                raise ValueError("Provide effect_size or p_observed")
        
        # Calculate power
        chi2_power = GofChisquarePower()
        power = chi2_power.solve_power(
            effect_size=effect_size,
            nobs=n,
            alpha=alpha,
            n_bins=df + 1,
        )
        
        # Effect size interpretation
        if effect_size < 0.1:
            interp = "negligible"
        elif effect_size < 0.3:
            interp = "small"
        elif effect_size < 0.5:
            interp = "medium"
        else:
            interp = "large"
        
        # Cramér's V
        cramers_v = None
        if n_rows is not None and n_cols is not None:
            min_dim = min(n_rows - 1, n_cols - 1)
            if min_dim > 0:
                cramers_v = effect_size / math.sqrt(min_dim)
        
        interp_text = (
            f"With N = {n}, effect size w = {effect_size:.3f}, df = {df}, "
            f"the study has {power*100:.1f}% power at α = {alpha}."
        )
        
        recs = []
        if power < 0.80:
            needed_n = ChiSquarePowerAnalysis.calculate_sample_size(
                effect_size=effect_size,
                alpha=alpha,
                power=0.80,
                df=df,
            ).n
            recs.append(f"Power is {power*100:.1f}%. Need N = {needed_n} for 80% power.")
        
        return ChiSquarePowerResult(
            test_type=test_type,
            scenario="power",
            n=n,
            power=power,
            effect_size_w=effect_size,
            df=df,
            alpha=alpha,
            n_bins=n_bins,
            n_rows=n_rows,
            n_cols=n_cols,
            cramers_v=cramers_v,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
        )
    
    @staticmethod
    def _sensitivity_analysis(
        effect_size: float,
        df: int,
        alpha: float,
        power_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for chi-square"""
        if power_range is None:
            power_range = [0.70, 0.80, 0.85, 0.90, 0.95]
        
        chi2_power = GofChisquarePower()
        
        by_power = []
        for pwr in power_range:
            n = chi2_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=pwr,
                n_bins=df + 1,
            )
            by_power.append({
                "power": pwr,
                "n": int(math.ceil(n)),
            })
        
        # By df
        by_df = []
        for d in [1, 2, 4, 6, 8]:
            n = chi2_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=0.80,
                n_bins=d + 1,
            )
            by_df.append({
                "df": d,
                "n": int(math.ceil(n)),
            })
        
        return {
            "by_power_level": by_power,
            "by_df": by_df,
        }


# =============================================================================
# Convenience Functions for Phase 6.2
# =============================================================================

def calculate_anova_sample_size(
    effect_size: Optional[float] = None,
    k_groups: int = 3,
    alpha: float = 0.05,
    power: float = 0.80,
    group_means: Optional[List[float]] = None,
    pooled_sd: Optional[float] = None,
    eta_squared: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate sample size for one-way ANOVA (MCP-friendly wrapper).
    
    Args:
        effect_size: Cohen's f (small=0.1, medium=0.25, large=0.4)
        k_groups: Number of groups
        alpha: Significance level
        power: Desired power
        group_means: Group means to calculate effect size
        pooled_sd: Pooled standard deviation
        eta_squared: Eta-squared to convert
        
    Returns:
        Dictionary with sample size results
    """
    result = ANOVAPowerAnalysis.calculate_sample_size(
        effect_size=effect_size,
        k_groups=k_groups,
        alpha=alpha,
        power=power,
        group_means=group_means,
        pooled_sd=pooled_sd,
        eta_squared=eta_squared,
    )
    return result.to_dict()


def calculate_anova_power(
    n_per_group: int,
    effect_size: Optional[float] = None,
    k_groups: int = 3,
    alpha: float = 0.05,
    group_means: Optional[List[float]] = None,
    pooled_sd: Optional[float] = None,
    eta_squared: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate power for one-way ANOVA (MCP-friendly wrapper).
    
    Args:
        n_per_group: Sample size per group
        effect_size: Cohen's f
        k_groups: Number of groups
        alpha: Significance level
        group_means: Group means to calculate effect size
        pooled_sd: Pooled standard deviation
        eta_squared: Eta-squared to convert
        
    Returns:
        Dictionary with power results
    """
    result = ANOVAPowerAnalysis.calculate_power(
        n_per_group=n_per_group,
        effect_size=effect_size,
        k_groups=k_groups,
        alpha=alpha,
        group_means=group_means,
        pooled_sd=pooled_sd,
        eta_squared=eta_squared,
    )
    return result.to_dict()


def calculate_chisquare_sample_size(
    effect_size: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
    df: Optional[int] = None,
    n_bins: Optional[int] = None,
    n_rows: Optional[int] = None,
    n_cols: Optional[int] = None,
    p_observed: Optional[List[float]] = None,
    p_expected: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate sample size for chi-square test (MCP-friendly wrapper).
    
    Args:
        effect_size: Cohen's w (small=0.1, medium=0.3, large=0.5)
        alpha: Significance level
        power: Desired power
        df: Degrees of freedom
        n_bins: Number of categories (goodness-of-fit)
        n_rows: Rows in contingency table
        n_cols: Columns in contingency table
        p_observed: Observed proportions
        p_expected: Expected proportions
        
    Returns:
        Dictionary with sample size results
    """
    result = ChiSquarePowerAnalysis.calculate_sample_size(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        df=df,
        n_bins=n_bins,
        n_rows=n_rows,
        n_cols=n_cols,
        p_observed=p_observed,
        p_expected=p_expected,
    )
    return result.to_dict()


def calculate_chisquare_power(
    n: int,
    effect_size: Optional[float] = None,
    alpha: float = 0.05,
    df: Optional[int] = None,
    n_bins: Optional[int] = None,
    n_rows: Optional[int] = None,
    n_cols: Optional[int] = None,
    p_observed: Optional[List[float]] = None,
    p_expected: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate power for chi-square test (MCP-friendly wrapper).
    
    Args:
        n: Sample size
        effect_size: Cohen's w
        alpha: Significance level
        df: Degrees of freedom
        n_bins: Number of categories
        n_rows: Rows in contingency table
        n_cols: Columns in contingency table
        p_observed: Observed proportions
        p_expected: Expected proportions
        
    Returns:
        Dictionary with power results
    """
    result = ChiSquarePowerAnalysis.calculate_power(
        n=n,
        effect_size=effect_size,
        alpha=alpha,
        df=df,
        n_bins=n_bins,
        n_rows=n_rows,
        n_cols=n_cols,
        p_observed=p_observed,
        p_expected=p_expected,
    )
    return result.to_dict()


# =============================================================================
# Phase 6.3: Survival Analysis Power Analysis
# =============================================================================

def hazard_ratio_to_log_hr(hazard_ratio: float) -> float:
    """Convert hazard ratio to log hazard ratio."""
    return math.log(hazard_ratio)


def log_hr_to_hazard_ratio(log_hr: float) -> float:
    """Convert log hazard ratio to hazard ratio."""
    return math.exp(log_hr)


def events_from_survival(
    n: int,
    prob_event: float,
    follow_up_time: Optional[float] = None,
    median_survival: Optional[float] = None,
) -> int:
    """
    Estimate number of events from sample size and event probability.
    
    Args:
        n: Total sample size
        prob_event: Probability of observing event (1 - censoring rate)
        follow_up_time: Follow-up duration
        median_survival: Median survival time (alternative calculation)
        
    Returns:
        Expected number of events
    """
    return int(math.ceil(n * prob_event))


def sample_size_from_events(
    n_events: int,
    prob_event: float,
) -> int:
    """
    Calculate sample size needed to observe required events.
    
    Args:
        n_events: Required number of events
        prob_event: Probability of event (1 - censoring rate)
        
    Returns:
        Required sample size
    """
    if prob_event <= 0 or prob_event > 1:
        raise ValueError("prob_event must be between 0 and 1")
    return int(math.ceil(n_events / prob_event))


@dataclass
class SurvivalPowerResult:
    """Result of survival analysis power calculation"""
    
    test_type: str = "log-rank test"
    scenario: str = "sample_size"  # or "power" or "events"
    
    # Main results
    total_n: Optional[int] = None
    n_per_group: Optional[int] = None
    n_events: Optional[int] = None
    events_per_group: Optional[int] = None
    power: Optional[float] = None
    
    # Parameters
    hazard_ratio: Optional[float] = None
    log_hazard_ratio: Optional[float] = None
    alpha: float = 0.05
    alternative: str = "two-sided"
    allocation_ratio: float = 1.0  # n2/n1
    
    # Event/survival parameters
    prob_event: Optional[float] = None  # Overall event probability
    prob_event_control: Optional[float] = None
    prob_event_treatment: Optional[float] = None
    median_survival_control: Optional[float] = None
    median_survival_treatment: Optional[float] = None
    accrual_time: Optional[float] = None
    follow_up_time: Optional[float] = None
    
    # Interpretation
    effect_size_interpretation: str = ""
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    
    # Metadata
    method: str = "Schoenfeld formula"
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_type": self.test_type,
            "scenario": self.scenario,
            "results": {
                "total_n": self.total_n,
                "n_per_group": self.n_per_group,
                "n_events": self.n_events,
                "events_per_group": self.events_per_group,
                "power": safe_round(self.power, 4),
            },
            "parameters": {
                "hazard_ratio": safe_round(self.hazard_ratio, 4),
                "log_hazard_ratio": safe_round(self.log_hazard_ratio, 4),
                "alpha": self.alpha,
                "alternative": self.alternative,
                "allocation_ratio": self.allocation_ratio,
                "prob_event": safe_round(self.prob_event, 4),
                "prob_event_control": safe_round(self.prob_event_control, 4),
                "prob_event_treatment": safe_round(self.prob_event_treatment, 4),
                "median_survival_control": self.median_survival_control,
                "median_survival_treatment": self.median_survival_treatment,
                "accrual_time": self.accrual_time,
                "follow_up_time": self.follow_up_time,
            },
            "effect_size_interpretation": self.effect_size_interpretation,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "sensitivity_analysis": self.sensitivity_analysis,
            "method": self.method,
            "notes": self.notes,
        }


class SurvivalPowerAnalysis:
    """
    Power analysis for survival analysis (time-to-event data).
    
    Supports:
    - Log-rank test (comparing two survival curves)
    - Sample size calculation given hazard ratio
    - Power calculation given sample size/events
    - Events calculation
    
    Methods:
    - Schoenfeld (1981) formula for log-rank test
    - Freedman (1982) formula (alternative)
    
    Key parameters:
    - Hazard Ratio (HR): Effect size for survival
      - HR = 1: No difference
      - HR < 1: Treatment reduces hazard (better survival)
      - HR > 1: Treatment increases hazard (worse survival)
    - HR = 0.5 means treatment halves the hazard
    - HR = 2.0 means treatment doubles the hazard
    """
    
    @staticmethod
    def calculate_events(
        hazard_ratio: float,
        alpha: float = 0.05,
        power: float = 0.80,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
        _include_sensitivity: bool = True,  # Internal flag to prevent recursion
    ) -> SurvivalPowerResult:
        """
        Calculate required number of events for log-rank test.
        
        Uses Schoenfeld (1981) formula:
        d = (z_α/2 + z_β)² * (1 + r)² / (r * (log(HR))²)
        
        Args:
            hazard_ratio: Expected hazard ratio (treatment/control)
            alpha: Significance level
            power: Desired power
            allocation_ratio: n_treatment / n_control (default: 1)
            alternative: "two-sided" or "one-sided"
            
        Returns:
            SurvivalPowerResult with required events
        """
        if hazard_ratio <= 0:
            raise ValueError("hazard_ratio must be positive")
        if hazard_ratio == 1:
            raise ValueError("hazard_ratio = 1 means no effect, cannot calculate sample size")
        
        # Z-values
        if alternative == "two-sided":
            z_alpha = stats.norm.ppf(1 - alpha / 2)
        else:
            z_alpha = stats.norm.ppf(1 - alpha)
        z_beta = stats.norm.ppf(power)
        
        # Schoenfeld formula
        log_hr = math.log(hazard_ratio)
        r = allocation_ratio
        
        # Number of events needed
        d = ((z_alpha + z_beta) ** 2) * ((1 + r) ** 2) / (r * (log_hr ** 2))
        n_events = int(math.ceil(d))
        
        # Events per group (assuming equal event rates)
        events_control = int(math.ceil(n_events / (1 + r)))
        events_treatment = n_events - events_control
        
        # Effect size interpretation
        if hazard_ratio < 0.5 or hazard_ratio > 2.0:
            interp = "large"
        elif hazard_ratio < 0.67 or hazard_ratio > 1.5:
            interp = "medium"
        elif hazard_ratio < 0.8 or hazard_ratio > 1.25:
            interp = "small"
        else:
            interp = "negligible"
        
        # Sensitivity analysis (only if not in recursive call)
        sensitivity = None
        if _include_sensitivity:
            sensitivity = SurvivalPowerAnalysis._events_sensitivity(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                allocation_ratio=r,
                alternative=alternative,
            )
        
        # Interpretation text
        hr_direction = "reduces" if hazard_ratio < 1 else "increases"
        hr_pct = abs(1 - hazard_ratio) * 100
        interp_text = (
            f"To detect HR = {hazard_ratio:.2f} ({hr_direction} hazard by {hr_pct:.0f}%) "
            f"with {power*100:.0f}% power at α = {alpha}, "
            f"you need to observe {n_events} events total."
        )
        
        recs = []
        if n_events > 500:
            recs.append(f"Large number of events ({n_events}) required. Consider longer follow-up or higher-risk population.")
        recs.append(f"With {int((1-power)*100)}% of events censored, total N ≈ {int(n_events/0.7)} (assuming 70% event rate).")
        if hazard_ratio > 0.9 and hazard_ratio < 1.1:
            recs.append("Small HR near 1.0 requires many events. Verify clinical significance.")
        
        return SurvivalPowerResult(
            test_type="log-rank test",
            scenario="events",
            n_events=n_events,
            events_per_group=events_control if r == 1 else None,
            hazard_ratio=hazard_ratio,
            log_hazard_ratio=log_hr,
            alpha=alpha,
            power=power,
            alternative=alternative,
            allocation_ratio=r,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
            sensitivity_analysis=sensitivity,
            method="Schoenfeld (1981) formula",
        )
    
    @staticmethod
    def calculate_sample_size(
        hazard_ratio: float,
        alpha: float = 0.05,
        power: float = 0.80,
        prob_event: float = 0.70,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
        accrual_time: Optional[float] = None,
        follow_up_time: Optional[float] = None,
        _include_sensitivity: bool = True,  # Internal flag to prevent recursion
    ) -> SurvivalPowerResult:
        """
        Calculate total sample size for log-rank test.
        
        Args:
            hazard_ratio: Expected hazard ratio
            alpha: Significance level
            power: Desired power
            prob_event: Expected proportion of events (1 - censoring)
            allocation_ratio: n_treatment / n_control
            alternative: "two-sided" or "one-sided"
            accrual_time: Time to recruit all patients (months)
            follow_up_time: Additional follow-up after last enrollment
            
        Returns:
            SurvivalPowerResult with sample size
        """
        # First get required events
        events_result = SurvivalPowerAnalysis.calculate_events(
            hazard_ratio=hazard_ratio,
            alpha=alpha,
            power=power,
            allocation_ratio=allocation_ratio,
            alternative=alternative,
            _include_sensitivity=False,  # Don't include sensitivity in nested call
        )
        
        n_events = events_result.n_events
        
        # Calculate sample size from events
        if prob_event <= 0 or prob_event > 1:
            raise ValueError("prob_event must be between 0 and 1")
        
        total_n = int(math.ceil(n_events / prob_event))
        r = allocation_ratio
        n_control = int(math.ceil(total_n / (1 + r)))
        n_treatment = total_n - n_control
        
        # Sensitivity analysis (only if not in recursive call)
        sensitivity = None
        if _include_sensitivity:
            sensitivity = SurvivalPowerAnalysis._sample_size_sensitivity(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                allocation_ratio=r,
                alternative=alternative,
            )
        
        # Interpretation
        hr_direction = "reduces" if hazard_ratio < 1 else "increases"
        hr_pct = abs(1 - hazard_ratio) * 100
        interp_text = (
            f"To detect HR = {hazard_ratio:.2f} ({hr_direction} hazard by {hr_pct:.0f}%) "
            f"with {power*100:.0f}% power at α = {alpha}, assuming {prob_event*100:.0f}% event rate, "
            f"you need N = {total_n} ({n_control} control + {n_treatment} treatment)."
        )
        
        recs = events_result.recommendations.copy()
        if prob_event < 0.5:
            recs.append(f"Low event rate ({prob_event*100:.0f}%) increases sample size. Consider longer follow-up.")
        
        return SurvivalPowerResult(
            test_type="log-rank test",
            scenario="sample_size",
            total_n=total_n,
            n_per_group=n_control if r == 1 else None,
            n_events=n_events,
            power=power,
            hazard_ratio=hazard_ratio,
            log_hazard_ratio=math.log(hazard_ratio),
            alpha=alpha,
            alternative=alternative,
            allocation_ratio=r,
            prob_event=prob_event,
            accrual_time=accrual_time,
            follow_up_time=follow_up_time,
            effect_size_interpretation=events_result.effect_size_interpretation,
            interpretation=interp_text,
            recommendations=recs,
            sensitivity_analysis=sensitivity,
            method="Schoenfeld (1981) formula",
        )
    
    @staticmethod
    def calculate_power(
        n_events: Optional[int] = None,
        total_n: Optional[int] = None,
        hazard_ratio: float = 1.5,
        alpha: float = 0.05,
        prob_event: float = 0.70,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> SurvivalPowerResult:
        """
        Calculate power for log-rank test given sample size or events.
        
        Args:
            n_events: Number of events (if known)
            total_n: Total sample size (events calculated from prob_event)
            hazard_ratio: Expected hazard ratio
            alpha: Significance level
            prob_event: Event probability (used if n_events not provided)
            allocation_ratio: n_treatment / n_control
            alternative: "two-sided" or "one-sided"
            
        Returns:
            SurvivalPowerResult with power
        """
        if hazard_ratio <= 0 or hazard_ratio == 1:
            raise ValueError("hazard_ratio must be positive and not equal to 1")
        
        # Determine number of events
        if n_events is None:
            if total_n is None:
                raise ValueError("Provide either n_events or total_n")
            n_events = int(math.ceil(total_n * prob_event))
        
        if total_n is None:
            total_n = int(math.ceil(n_events / prob_event))
        
        # Calculate power using inverse Schoenfeld formula
        log_hr = math.log(hazard_ratio)
        r = allocation_ratio
        
        if alternative == "two-sided":
            z_alpha = stats.norm.ppf(1 - alpha / 2)
        else:
            z_alpha = stats.norm.ppf(1 - alpha)
        
        # From: d = ((z_α + z_β)² * (1+r)²) / (r * log_hr²)
        # Solve for z_β: z_β = sqrt(d * r * log_hr² / (1+r)²) - z_α
        z_beta = math.sqrt(n_events * r * (log_hr ** 2) / ((1 + r) ** 2)) - z_alpha
        power = stats.norm.cdf(z_beta)
        
        # Calculate per-group if equal allocation
        n_per_group = total_n // 2 if r == 1 else None
        
        # Effect size interpretation
        if hazard_ratio < 0.5 or hazard_ratio > 2.0:
            interp = "large"
        elif hazard_ratio < 0.67 or hazard_ratio > 1.5:
            interp = "medium"
        elif hazard_ratio < 0.8 or hazard_ratio > 1.25:
            interp = "small"
        else:
            interp = "negligible"
        
        # Interpretation
        interp_text = (
            f"With {n_events} events (N = {total_n}), HR = {hazard_ratio:.2f}, "
            f"the study has {power*100:.1f}% power at α = {alpha}."
        )
        
        recs = []
        if power < 0.80:
            needed = SurvivalPowerAnalysis.calculate_events(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=0.80,
                allocation_ratio=r,
                alternative=alternative,
            )
            recs.append(f"Power is {power*100:.1f}%. Need {needed.n_events} events for 80% power.")
        
        return SurvivalPowerResult(
            test_type="log-rank test",
            scenario="power",
            total_n=total_n,
            n_per_group=n_per_group,
            n_events=n_events,
            power=power,
            hazard_ratio=hazard_ratio,
            log_hazard_ratio=log_hr,
            alpha=alpha,
            alternative=alternative,
            allocation_ratio=r,
            prob_event=prob_event,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
            method="Schoenfeld (1981) formula",
        )
    
    @staticmethod
    def calculate_from_median_survival(
        median_control: float,
        median_treatment: float,
        alpha: float = 0.05,
        power: float = 0.80,
        accrual_time: float = 12,
        follow_up_time: float = 12,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> SurvivalPowerResult:
        """
        Calculate sample size from median survival times.
        
        Assumes exponential survival (constant hazard).
        HR = log(0.5) / median_control * median_treatment / log(0.5)
           = median_control / median_treatment
        
        Args:
            median_control: Median survival in control (same units as times)
            median_treatment: Median survival in treatment
            alpha: Significance level
            power: Desired power
            accrual_time: Enrollment period
            follow_up_time: Follow-up after last enrollment
            allocation_ratio: n_treatment / n_control
            alternative: "two-sided" or "one-sided"
            
        Returns:
            SurvivalPowerResult with sample size
        """
        if median_control <= 0 or median_treatment <= 0:
            raise ValueError("Median survival times must be positive")
        
        # Calculate hazard ratio (assuming exponential)
        # Under exponential: hazard = log(2) / median
        hazard_control = math.log(2) / median_control
        hazard_treatment = math.log(2) / median_treatment
        hazard_ratio = hazard_treatment / hazard_control
        
        # Estimate event probability over study period
        total_time = accrual_time + follow_up_time
        # Average follow-up assuming uniform accrual
        avg_follow_up = follow_up_time + accrual_time / 2
        
        # Event probability (exponential assumption)
        # P(event) ≈ 1 - exp(-hazard * avg_follow_up)
        avg_hazard = (hazard_control + hazard_treatment) / 2
        prob_event = 1 - math.exp(-avg_hazard * avg_follow_up)
        prob_event = min(prob_event, 0.95)  # Cap at 95%
        
        # Calculate sample size
        result = SurvivalPowerAnalysis.calculate_sample_size(
            hazard_ratio=hazard_ratio,
            alpha=alpha,
            power=power,
            prob_event=prob_event,
            allocation_ratio=allocation_ratio,
            alternative=alternative,
            accrual_time=accrual_time,
            follow_up_time=follow_up_time,
        )
        
        # Update with median survival info
        result.median_survival_control = median_control
        result.median_survival_treatment = median_treatment
        result.notes.append(f"Based on exponential survival assumption")
        result.notes.append(f"Estimated event rate: {prob_event*100:.0f}% over {total_time} months")
        
        return result
    
    @staticmethod
    def _events_sensitivity(
        hazard_ratio: float,
        alpha: float,
        allocation_ratio: float,
        alternative: str,
        power_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for events"""
        if power_range is None:
            power_range = [0.70, 0.80, 0.85, 0.90, 0.95]
        
        by_power = []
        for pwr in power_range:
            result = SurvivalPowerAnalysis.calculate_events(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=pwr,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
                _include_sensitivity=False,  # Prevent recursion
            )
            by_power.append({
                "power": pwr,
                "n_events": result.n_events,
            })
        
        # By hazard ratio
        by_hr = []
        for hr in [0.5, 0.6, 0.7, 0.8]:
            try:
                result = SurvivalPowerAnalysis.calculate_events(
                    hazard_ratio=hr,
                    alpha=alpha,
                    power=0.80,
                    allocation_ratio=allocation_ratio,
                    alternative=alternative,
                    _include_sensitivity=False,  # Prevent recursion
                )
                by_hr.append({
                    "hazard_ratio": hr,
                    "n_events": result.n_events,
                })
            except ValueError:
                pass
        
        return {
            "by_power_level": by_power,
            "by_hazard_ratio": by_hr,
        }
    
    @staticmethod
    def _sample_size_sensitivity(
        hazard_ratio: float,
        alpha: float,
        allocation_ratio: float,
        alternative: str,
        prob_event_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for sample size"""
        if prob_event_range is None:
            prob_event_range = [0.50, 0.60, 0.70, 0.80, 0.90]
        
        by_prob = []
        for prob in prob_event_range:
            result = SurvivalPowerAnalysis.calculate_sample_size(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=0.80,
                prob_event=prob,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
                _include_sensitivity=False,  # Prevent recursion
            )
            by_prob.append({
                "prob_event": prob,
                "total_n": result.total_n,
                "n_events": result.n_events,
            })
        
        return {
            "by_event_probability": by_prob,
        }


# =============================================================================
# Convenience Functions for Phase 6.3
# =============================================================================

def calculate_survival_events(
    hazard_ratio: float,
    alpha: float = 0.05,
    power: float = 0.80,
    allocation_ratio: float = 1.0,
    alternative: str = "two-sided",
) -> Dict[str, Any]:
    """
    Calculate required events for log-rank test (MCP-friendly wrapper).
    
    Args:
        hazard_ratio: Expected hazard ratio (treatment/control)
            - HR < 1: Treatment reduces hazard (better)
            - HR > 1: Treatment increases hazard (worse)
        alpha: Significance level
        power: Desired power
        allocation_ratio: n_treatment / n_control
        alternative: "two-sided" or "one-sided"
        
    Returns:
        Dictionary with required events
    """
    result = SurvivalPowerAnalysis.calculate_events(
        hazard_ratio=hazard_ratio,
        alpha=alpha,
        power=power,
        allocation_ratio=allocation_ratio,
        alternative=alternative,
    )
    return result.to_dict()


def calculate_survival_sample_size(
    hazard_ratio: float,
    alpha: float = 0.05,
    power: float = 0.80,
    prob_event: float = 0.70,
    allocation_ratio: float = 1.0,
    alternative: str = "two-sided",
    accrual_time: Optional[float] = None,
    follow_up_time: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate sample size for log-rank test (MCP-friendly wrapper).
    
    Args:
        hazard_ratio: Expected hazard ratio
        alpha: Significance level
        power: Desired power
        prob_event: Expected event rate (1 - censoring)
        allocation_ratio: n_treatment / n_control
        alternative: "two-sided" or "one-sided"
        accrual_time: Enrollment period (months)
        follow_up_time: Follow-up period (months)
        
    Returns:
        Dictionary with sample size
    """
    result = SurvivalPowerAnalysis.calculate_sample_size(
        hazard_ratio=hazard_ratio,
        alpha=alpha,
        power=power,
        prob_event=prob_event,
        allocation_ratio=allocation_ratio,
        alternative=alternative,
        accrual_time=accrual_time,
        follow_up_time=follow_up_time,
    )
    return result.to_dict()


def calculate_survival_power(
    hazard_ratio: float,
    n_events: Optional[int] = None,
    total_n: Optional[int] = None,
    alpha: float = 0.05,
    prob_event: float = 0.70,
    allocation_ratio: float = 1.0,
    alternative: str = "two-sided",
) -> Dict[str, Any]:
    """
    Calculate power for log-rank test (MCP-friendly wrapper).
    
    Args:
        hazard_ratio: Expected hazard ratio
        n_events: Number of events (if known)
        total_n: Sample size (events calculated from prob_event)
        alpha: Significance level
        prob_event: Event probability
        allocation_ratio: n_treatment / n_control
        alternative: "two-sided" or "one-sided"
        
    Returns:
        Dictionary with power
    """
    result = SurvivalPowerAnalysis.calculate_power(
        hazard_ratio=hazard_ratio,
        n_events=n_events,
        total_n=total_n,
        alpha=alpha,
        prob_event=prob_event,
        allocation_ratio=allocation_ratio,
        alternative=alternative,
    )
    return result.to_dict()


def calculate_survival_from_medians(
    median_control: float,
    median_treatment: float,
    alpha: float = 0.05,
    power: float = 0.80,
    accrual_time: float = 12,
    follow_up_time: float = 12,
    allocation_ratio: float = 1.0,
    alternative: str = "two-sided",
) -> Dict[str, Any]:
    """
    Calculate sample size from median survival times (MCP-friendly wrapper).
    
    Useful when you know expected median survival in each group.
    
    Args:
        median_control: Median survival in control group (months)
        median_treatment: Median survival in treatment group (months)
        alpha: Significance level
        power: Desired power
        accrual_time: Enrollment period (months)
        follow_up_time: Additional follow-up (months)
        allocation_ratio: n_treatment / n_control
        alternative: "two-sided" or "one-sided"
        
    Returns:
        Dictionary with sample size and hazard ratio
    """
    result = SurvivalPowerAnalysis.calculate_from_median_survival(
        median_control=median_control,
        median_treatment=median_treatment,
        alpha=alpha,
        power=power,
        accrual_time=accrual_time,
        follow_up_time=follow_up_time,
        allocation_ratio=allocation_ratio,
        alternative=alternative,
    )
    return result.to_dict()


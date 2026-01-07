"""
ANOVA Power Analysis Module

Power analysis for one-way ANOVA (F-test).

Contains:
    - ANOVAPowerResult: Result dataclass for ANOVA power calculations
    - ANOVAPowerAnalysis: Main analysis class
    - Helper functions for effect size conversion
    - Convenience wrapper functions for MCP tools
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
from statsmodels.stats.power import FTestAnovaPower

from .base import (
    interpret_effect_size,
    safe_round,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions for ANOVA
# =============================================================================

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


# =============================================================================
# Result Dataclass
# =============================================================================

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


# =============================================================================
# ANOVA Power Analysis Class
# =============================================================================

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
# Convenience Functions for MCP
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

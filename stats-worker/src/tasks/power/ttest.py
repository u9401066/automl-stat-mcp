"""
T-Test Power Analysis Module

Power analysis for t-tests and proportion tests.

Contains:
    - TTestPowerAnalysis: Two-sample, paired, and one-sample t-tests
    - ProportionPowerAnalysis: Two proportions and one proportion tests
    - Convenience wrapper functions for MCP tools
"""

import logging
import math
from typing import Any, Dict, Literal, Optional, cast

import numpy as np
from statsmodels.stats.power import (
    NormalIndPower,
    TTestIndPower,
    TTestPower,
)

from .base import (
    EffectSizeType,
    PowerAnalysisResult,
    TestType,
    cohens_d_from_means,
    cohens_h_from_proportions,
    interpret_effect_size,
)

logger = logging.getLogger(__name__)


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
                raise ValueError("Either effect_size or (mean1, mean2, sd) must be provided")

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
                f"with {power * 100:.0f}% power at α = {alpha}, "
                f"you need {n1} participants in group 1 and {n2} in group 2 "
                f"(total N = {total_n})."
            )
        elif test_type == "paired":
            interpretation = (
                f"To detect a {es_interpretation} effect (Cohen's d = {effect_size_abs:.3f}) "
                f"with {power * 100:.0f}% power at α = {alpha}, "
                f"you need {n1} pairs of measurements."
            )
        else:  # one-sample
            interpretation = (
                f"To detect a {es_interpretation} effect (Cohen's d = {effect_size_abs:.3f}) "
                f"with {power * 100:.0f}% power at α = {alpha}, "
                f"you need {n1} participants."
            )

        # Generate recommendations
        recommendations = []
        if es_interpretation == "small":
            recommendations.append(
                "Small effect sizes require large samples. Consider whether this effect is clinically meaningful."
            )
        if power < 0.80:
            recommendations.append(
                "Power < 80% may result in false negatives. Consider increasing sample size if feasible."
            )
        if total_n > 500:
            recommendations.append(
                "Large sample requirement. Consider pilot study first to verify effect size estimate."
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
                raise ValueError("Either effect_size or (mean1, mean2, sd) must be provided")

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
            f"and α = {alpha}, the study has {power * 100:.1f}% power."
        )

        recommendations = []
        if power < 0.80:
            recommendations.append("Power is below 80%. Consider increasing sample size to achieve adequate power.")
        if power > 0.95:
            recommendations.append(
                "Power > 95% may indicate over-sampling. Resources could be optimized with fewer participants."
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
                f"({p1 * 100:.1f}% vs {p2 * 100:.1f}%, Cohen's h = {effect_size_abs:.3f}) "
                f"with {power * 100:.0f}% power at α = {alpha}, "
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
                f"({p1 * 100:.1f}% vs {p0 * 100:.1f}%, Cohen's h = {effect_size_abs:.3f}) "
                f"with {power * 100:.0f}% power at α = {alpha}, "
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
            nnt = 1 / ard if ard > 0 else float("inf")
            recommendations.append(
                f"Absolute risk difference: {ard * 100:.1f}%. Number needed to treat (NNT): {nnt:.1f}."
            )

        if es_interpretation == "small":
            recommendations.append(
                "Small effect size requires large sample. Verify if this difference is clinically meaningful."
            )

        # Sensitivity analysis
        sensitivity = ProportionPowerAnalysis._sensitivity_analysis(
            p1=p1,
            p2=p2,
            p0=p0,
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
            p2_val = float(p2)
            effect_size = cohens_h_from_proportions(p1, p2_val)
            test_name = TestType.PROPORTION_TWO.value
            n2 = math.ceil(n * ratio)
            total_n = n + n2
        else:
            if p0 is None:
                raise ValueError("p0 is required for one-sample test")
            p0_val = float(p0)
            effect_size = cohens_h_from_proportions(p1, p0_val)
            test_name = TestType.PROPORTION_ONE.value
            n2 = None
            total_n = n

        effect_size_abs = abs(effect_size)

        analysis = NormalIndPower()
        power_val = analysis.solve_power(
            effect_size=effect_size_abs,
            nobs1=n,
            alpha=alpha,
            ratio=ratio if test_type == "two-sample" else 1.0,
            alternative=alternative,
        )
        power = float(power_val)

        es_interpretation = interpret_effect_size(effect_size_abs, "cohens_h")

        if test_type == "two-sample":
            interpretation = (
                f"With n = {n} per group, comparing {p1 * 100:.1f}% vs {p2_val * 100:.1f}% "
                f"(Cohen's h = {effect_size_abs:.3f}), "
                f"the study has {power * 100:.1f}% power at α = {alpha}."
            )
        else:
            interpretation = (
                f"With n = {n}, comparing {p1 * 100:.1f}% vs hypothesized {p0_val * 100:.1f}% "
                f"(Cohen's h = {effect_size_abs:.3f}), "
                f"the study has {power * 100:.1f}% power at α = {alpha}."
            )

        recommendations = []
        if power < 0.80:
            recommendations.append(
                f"Power is {power * 100:.1f}%, below the recommended 80%. Consider increasing sample size."
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
        comparison_p = p2 if p2 is not None else p0
        if comparison_p is None:
            return {}  # Should not happen given caller logic

        base_es = abs(cohens_h_from_proportions(p1, comparison_p))

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
            p2 - p1
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
                    p2_variations.append({"p2": round(new_p2, 3), "effect_size": round(es, 3), "n": math.ceil(n)})
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
        alternative=cast(Literal["two-sided", "larger", "smaller"], alternative),
        ratio=ratio,
        test_type=cast(Literal["two-sample", "paired", "one-sample"], test_type),
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
        alternative=cast(Literal["two-sided", "larger", "smaller"], alternative),
        ratio=ratio,
        test_type=cast(Literal["two-sample", "paired", "one-sample"], test_type),
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
        alternative=cast(Literal["two-sided", "larger", "smaller"], alternative),
        ratio=ratio,
        test_type=cast(Literal["two-sample", "one-sample"], test_type),
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
        alternative=cast(Literal["two-sided", "larger", "smaller"], alternative),
        ratio=ratio,
        test_type=cast(Literal["two-sample", "one-sample"], test_type),
    )
    return result.to_dict()

"""
T-test and Proportion Power Analysis Tools

Tools:
    - calculate_ttest_sample_size
    - calculate_ttest_power
    - calculate_effect_size
    - ttest_sensitivity_analysis
    - calculate_proportion_sample_size
    - calculate_proportion_power
    - proportion_sensitivity_analysis
"""
from typing import Any, Dict, List, Optional

from ..base import logger


def register_ttest_power_tools(mcp, stats_client):
    """Register t-test and proportion power analysis tools."""

    @mcp.tool()
    async def calculate_ttest_sample_size(
        effect_size: Optional[float] = None,
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        std: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        alternative: str = "two-sided",
        paired: bool = False,
    ) -> Dict[str, Any]:
        """
        📊 Calculate sample size for t-test (comparing two means).

        Use when planning a study comparing two groups on a continuous outcome.

        Args:
            effect_size: Cohen's d effect size
                - 0.20 = small effect
                - 0.50 = medium effect
                - 0.80 = large effect
            mean1: Expected mean in group 1 (alternative to effect_size)
            mean2: Expected mean in group 2 (alternative to effect_size)
            std: Standard deviation (required if using means)
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            alternative: "two-sided", "greater", or "less"
            paired: Whether this is a paired t-test (default: False)

        Returns:
            n_per_group: Required sample size per group
            total_n: Total sample size
            effect_size: Cohen's d used in calculation
            interpretation: Effect size interpretation

        Example:
            calculate_ttest_sample_size(effect_size=0.5, power=0.80)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_ttest_power(
                calculation_type="sample_size",
                effect_size=effect_size,
                mean1=mean1,
                mean2=mean2,
                std=std,
                alpha=alpha,
                power=power,
                alternative=alternative,
                paired=paired,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_ttest_sample_size error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_ttest_power(
        n_per_group: int,
        effect_size: Optional[float] = None,
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        std: Optional[float] = None,
        alpha: float = 0.05,
        alternative: str = "two-sided",
        paired: bool = False,
    ) -> Dict[str, Any]:
        """
        ⚡ Calculate statistical power for t-test given sample size.

        Use to evaluate whether your existing study has adequate power.

        Args:
            n_per_group: Sample size per group (or total n for paired)
            effect_size: Cohen's d effect size
            mean1: Expected mean in group 1
            mean2: Expected mean in group 2
            std: Standard deviation
            alpha: Significance level (default: 0.05)
            alternative: "two-sided", "greater", or "less"
            paired: Whether this is a paired t-test

        Returns:
            power: Calculated statistical power (0-1)
            interpretation: Power adequacy assessment
            recommendations: Suggestions if underpowered

        Example:
            calculate_ttest_power(n_per_group=30, effect_size=0.5)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_ttest_power(
                calculation_type="power",
                n_per_group=n_per_group,
                effect_size=effect_size,
                mean1=mean1,
                mean2=mean2,
                std=std,
                alpha=alpha,
                alternative=alternative,
                paired=paired,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_ttest_power error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_effect_size(
        mean1: float,
        mean2: float,
        std1: Optional[float] = None,
        std2: Optional[float] = None,
        pooled_std: Optional[float] = None,
        n1: Optional[int] = None,
        n2: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        🧮 Calculate Cohen's d effect size from means and SDs.

        Use when you have pilot data or literature values.

        Args:
            mean1: Mean of group 1
            mean2: Mean of group 2
            std1: Standard deviation of group 1
            std2: Standard deviation of group 2
            pooled_std: Pooled SD (alternative to std1/std2)
            n1: Sample size of group 1 (for weighted pooling)
            n2: Sample size of group 2 (for weighted pooling)

        Returns:
            cohens_d: Cohen's d effect size
            interpretation: small/medium/large
            mean_difference: Absolute difference
            pooled_sd: Pooled standard deviation used

        Example:
            calculate_effect_size(mean1=10, mean2=12, pooled_std=5)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_ttest_power(
                calculation_type="effect_size",
                mean1=mean1,
                mean2=mean2,
                std1=std1,
                std2=std2,
                pooled_std=pooled_std,
                n1=n1,
                n2=n2,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_effect_size error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def ttest_sensitivity_analysis(
        n_per_group: int,
        effect_sizes: Optional[List[float]] = None,
        powers: Optional[List[float]] = None,
        alphas: Optional[List[float]] = None,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        📈 Sensitivity analysis showing power across different scenarios.

        Generates a table showing how power changes with different
        effect sizes, sample sizes, or alpha levels.

        Args:
            n_per_group: Base sample size per group
            effect_sizes: List of effect sizes to test
                (default: [0.2, 0.3, 0.4, 0.5, 0.6, 0.8])
            powers: Target powers to show required n
            alphas: List of alpha levels to test
            alternative: "two-sided", "greater", or "less"

        Returns:
            sensitivity_table: Power for each effect size
            detectable_effect: Minimum detectable effect at 80% power
            recommendations: Study design suggestions

        Example:
            ttest_sensitivity_analysis(n_per_group=50)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_ttest_power(
                calculation_type="sensitivity",
                n_per_group=n_per_group,
                effect_sizes=effect_sizes,
                powers=powers,
                alphas=alphas,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"ttest_sensitivity_analysis error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_proportion_sample_size(
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power: float = 0.80,
        alternative: str = "two-sided",
        allocation_ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """
        📊 Calculate sample size for comparing two proportions.

        Use when comparing success rates, response rates, or binary outcomes.

        Args:
            p1: Expected proportion in group 1 (e.g., 0.30 for 30%)
            p2: Expected proportion in group 2 (e.g., 0.50 for 50%)
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            alternative: "two-sided", "greater", or "less"
            allocation_ratio: n2/n1 ratio (default: 1.0 for equal groups)

        Returns:
            n1: Sample size for group 1
            n2: Sample size for group 2
            total_n: Total sample size
            effect_size_h: Cohen's h effect size

        Example:
            calculate_proportion_sample_size(p1=0.30, p2=0.50)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_proportion_power(
                calculation_type="sample_size",
                p1=p1,
                p2=p2,
                alpha=alpha,
                power=power,
                alternative=alternative,
                allocation_ratio=allocation_ratio,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_proportion_sample_size error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_proportion_power(
        p1: float,
        p2: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        ⚡ Calculate power for comparing two proportions given sample size.

        Args:
            p1: Expected proportion in group 1
            p2: Expected proportion in group 2
            n1: Sample size for group 1
            n2: Sample size for group 2 (default: same as n1)
            alpha: Significance level (default: 0.05)
            alternative: "two-sided", "greater", or "less"

        Returns:
            power: Calculated statistical power
            interpretation: Power adequacy assessment
            recommendations: Suggestions if underpowered

        Example:
            calculate_proportion_power(p1=0.30, p2=0.50, n1=100)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_proportion_power(
                calculation_type="power",
                p1=p1,
                p2=p2,
                n1=n1,
                n2=n2,
                alpha=alpha,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_proportion_power error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def proportion_sensitivity_analysis(
        p1: float,
        p2_values: Optional[List[float]] = None,
        n_values: Optional[List[int]] = None,
        alpha: float = 0.05,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        📈 Sensitivity analysis for proportion comparisons.

        Shows how power changes across different proportions
        and sample sizes.

        Args:
            p1: Baseline proportion (control group)
            p2_values: List of treatment proportions to evaluate
            n_values: List of sample sizes to evaluate
            alpha: Significance level
            alternative: "two-sided", "greater", or "less"

        Returns:
            sensitivity_table: Power for each combination
            minimum_detectable: Smallest detectable difference
            recommendations: Study design suggestions

        Example:
            proportion_sensitivity_analysis(
                p1=0.30,
                p2_values=[0.40, 0.45, 0.50],
                n_values=[50, 100, 150, 200]
            )
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_proportion_power(
                calculation_type="sensitivity",
                p1=p1,
                p2_values=p2_values,
                n_values=n_values,
                alpha=alpha,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"proportion_sensitivity_analysis error: {e}")
            return {"status": "error", "error": str(e)}

    logger.info("T-test/Proportion power tools registered: 7 tools")

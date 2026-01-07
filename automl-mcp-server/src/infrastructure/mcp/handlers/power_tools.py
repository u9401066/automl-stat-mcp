"""
Consolidated Power Analysis Tools for MCP

Combines multiple power analysis tools into unified interfaces:
- power_ttest: T-test power/sample size (replaces 3 tools)
- power_proportion: Proportion power/sample size (replaces 3 tools)
- power_anova: ANOVA power/sample size (replaces 3 tools)
- power_chisquare: Chi-square power/sample size (replaces 3 tools)
- power_survival: Survival power/sample size (replaces 5 tools)
"""
import logging
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_power_tools(mcp: FastMCP, stats_client) -> None:
    """Register consolidated power analysis tools"""

    @mcp.tool()
    async def power_ttest(
        effect_size: float,
        mode: str = "sample_size",
        n1: Optional[int] = None,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        test_type: str = "two-sample",
        alternative: str = "two-sided",
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        pooled_sd: Optional[float] = None,
    ) -> dict:
        """
        📊 T-test Power Analysis (unified tool).

        Combines sample size calculation, power calculation, and sensitivity analysis.

        **Modes:**
        - `sample_size`: Calculate required N given effect size and power
        - `power`: Calculate achieved power given N
        - `sensitivity`: Show power across range of N values
        - `effect_size`: Calculate effect size from means and SD

        **Effect Size (Cohen's d):**
        - 0.2 = small, 0.5 = medium, 0.8 = large
        - Or provide mean1, mean2, pooled_sd to calculate

        Args:
            effect_size: Cohen's d (or provide means + SD)
            mode: "sample_size" | "power" | "sensitivity" | "effect_size"
            n1: Sample size group 1 (for power/sensitivity mode)
            n2: Sample size group 2 (optional, defaults to n1)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80, for sample_size mode)
            ratio: n2/n1 ratio (default: 1.0)
            test_type: "two-sample" | "paired" | "one-sample"
            alternative: "two-sided" | "larger" | "smaller"
            mean1, mean2, pooled_sd: For effect_size calculation

        Returns:
            Mode-specific results plus:
            - parameters: All input parameters
            - interpretation: Plain-language explanation
            - recommendations: Practical suggestions

        Examples:
            # Calculate sample size for medium effect
            power_ttest(effect_size=0.5, mode="sample_size")

            # Check power with 50 per group
            power_ttest(effect_size=0.5, mode="power", n1=50)

            # Calculate effect size from means
            power_ttest(effect_size=0, mode="effect_size", mean1=100, mean2=115, pooled_sd=30)
        """
        try:
            # Mode: effect_size calculation
            if mode == "effect_size":
                if mean1 is not None and mean2 is not None and pooled_sd is not None:
                    d = abs(mean1 - mean2) / pooled_sd
                    interpretation = "small" if d < 0.5 else "medium" if d < 0.8 else "large"
                    return {
                        "status": "success",
                        "effect_size": round(d, 4),
                        "effect_type": "Cohen's d",
                        "interpretation": interpretation,
                        "formula": f"|{mean1} - {mean2}| / {pooled_sd}",
                        "recommendation": f"Use effect_size={round(d, 2)} for power analysis"
                    }
                else:
                    return {"status": "error", "error": "Provide mean1, mean2, and pooled_sd for effect_size mode"}

            # Mode: sample_size calculation
            if mode == "sample_size":
                result = await stats_client.calculate_ttest_power(
                    effect_size=effect_size,
                    alpha=alpha,
                    power=power,
                    n=None,
                    ratio=ratio,
                    alternative=alternative,
                )
                return result

            # Mode: power calculation
            if mode == "power":
                if n1 is None:
                    return {"status": "error", "error": "Provide n1 for power calculation"}
                result = await stats_client.calculate_ttest_power(
                    effect_size=effect_size,
                    alpha=alpha,
                    power=None,
                    n=n1,
                    ratio=1.0 if n2 is None else n2 / n1,
                    alternative=alternative,
                )
                return result

            # Mode: sensitivity analysis
            if mode == "sensitivity":
                if n1 is None:
                    n_range = [20, 30, 50, 75, 100, 150, 200]
                else:
                    n_range = [int(n1 * m) for m in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]]

                results = []
                for n in n_range:
                    r = await stats_client.calculate_ttest_power(
                        effect_size=effect_size,
                        alpha=alpha,
                        power=None,
                        n=n,
                        ratio=ratio,
                        alternative=alternative,
                    )
                    if r.get("status") == "success":
                        results.append({"n_per_group": n, "power": r.get("power", r.get("achieved_power"))})

                return {
                    "status": "success",
                    "sensitivity_table": results,
                    "parameters": {"effect_size": effect_size, "alpha": alpha},
                    "recommendation": "Choose n where power >= 0.80"
                }

            return {"status": "error", "error": f"Unknown mode: {mode}. Use: sample_size, power, sensitivity, effect_size"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def power_proportion(
        p1: float,
        p2: float,
        mode: str = "sample_size",
        n1: Optional[int] = None,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> dict:
        """
        📊 Proportion Comparison Power Analysis (unified tool).

        For comparing rates/percentages between groups (response rates, event rates).

        **Modes:**
        - `sample_size`: Calculate required N given proportions and power
        - `power`: Calculate achieved power given N
        - `sensitivity`: Show power across range of N values

        Args:
            p1: Proportion in group 1 (e.g., 0.30 for 30%)
            p2: Proportion in group 2 (e.g., 0.45 for 45%)
            mode: "sample_size" | "power" | "sensitivity"
            n1, n2: Sample sizes (for power/sensitivity mode)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            ratio: n2/n1 ratio (default: 1.0)
            alternative: "two-sided" | "larger" | "smaller"

        Returns:
            Mode-specific results with effect size (Cohen's h)

        Examples:
            # Control 30%, Treatment 45%
            power_proportion(p1=0.30, p2=0.45, mode="sample_size")

            # Check power with 100 per group
            power_proportion(p1=0.30, p2=0.45, mode="power", n1=100)
        """
        try:
            import math
            # Calculate Cohen's h
            h = 2 * (math.asin(math.sqrt(p2)) - math.asin(math.sqrt(p1)))

            if mode == "sample_size":
                result = await stats_client.calculate_proportion_power(
                    p1=p1, p2=p2, alpha=alpha, power=power, n=None, ratio=ratio, alternative=alternative
                )
                if isinstance(result, dict):
                    result["effect_size_h"] = round(abs(h), 4)
                return result

            if mode == "power":
                if n1 is None:
                    return {"status": "error", "error": "Provide n1 for power calculation"}
                result = await stats_client.calculate_proportion_power(
                    p1=p1, p2=p2, alpha=alpha, power=None, n=n1,
                    ratio=1.0 if n2 is None else n2 / n1, alternative=alternative
                )
                if isinstance(result, dict):
                    result["effect_size_h"] = round(abs(h), 4)
                return result

            if mode == "sensitivity":
                n_range = [50, 100, 150, 200, 300, 500] if n1 is None else [int(n1 * m) for m in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]]
                results = []
                for n in n_range:
                    r = await stats_client.calculate_proportion_power(
                        p1=p1, p2=p2, alpha=alpha, power=None, n=n, ratio=ratio, alternative=alternative
                    )
                    if r.get("status") == "success":
                        results.append({"n_per_group": n, "power": r.get("power", r.get("achieved_power"))})
                return {
                    "status": "success",
                    "sensitivity_table": results,
                    "effect_size_h": round(abs(h), 4),
                    "parameters": {"p1": p1, "p2": p2, "alpha": alpha}
                }

            return {"status": "error", "error": f"Unknown mode: {mode}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def power_anova(
        effect_size: float,
        k: int,
        mode: str = "sample_size",
        n: Optional[int] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
    ) -> dict:
        """
        📊 ANOVA Power Analysis (unified tool).

        For comparing means across 3+ groups.

        **Modes:**
        - `sample_size`: Calculate required N per group
        - `power`: Calculate achieved power given N
        - `effect_size`: Calculate f from group means and SD

        **Effect Size (Cohen's f):**
        - 0.10 = small, 0.25 = medium, 0.40 = large

        Args:
            effect_size: Cohen's f (or provide group_means + pooled_sd)
            k: Number of groups
            mode: "sample_size" | "power" | "effect_size"
            n: Sample size per group (for power mode)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            group_means: List of group means (for effect_size mode)
            pooled_sd: Pooled standard deviation (for effect_size mode)

        Returns:
            Mode-specific results

        Examples:
            # 3 groups, medium effect
            power_anova(effect_size=0.25, k=3, mode="sample_size")

            # Calculate f from means
            power_anova(effect_size=0, k=3, mode="effect_size",
                       group_means=[10, 12, 15], pooled_sd=5)
        """
        try:
            import math

            if mode == "effect_size":
                if group_means and pooled_sd:
                    grand_mean = sum(group_means) / len(group_means)
                    var_between = sum((m - grand_mean)**2 for m in group_means) / len(group_means)
                    f = math.sqrt(var_between) / pooled_sd
                    interpretation = "small" if f < 0.25 else "medium" if f < 0.40 else "large"
                    return {
                        "status": "success",
                        "effect_size_f": round(f, 4),
                        "interpretation": interpretation,
                        "parameters": {"group_means": group_means, "pooled_sd": pooled_sd}
                    }
                return {"status": "error", "error": "Provide group_means and pooled_sd for effect_size mode"}

            if mode == "sample_size":
                result = await stats_client.calculate_anova_power(
                    effect_size=effect_size, k=k, alpha=alpha, power=power, n=None
                )
                return result

            if mode == "power":
                if n is None:
                    return {"status": "error", "error": "Provide n for power calculation"}
                result = await stats_client.calculate_anova_power(
                    effect_size=effect_size, k=k, alpha=alpha, power=None, n=n
                )
                return result

            return {"status": "error", "error": f"Unknown mode: {mode}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def power_chisquare(
        effect_size: float,
        df: int,
        mode: str = "sample_size",
        n: Optional[int] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        observed: Optional[List[List[int]]] = None,
    ) -> dict:
        """
        📊 Chi-square Power Analysis (unified tool).

        For categorical data independence tests.

        **Modes:**
        - `sample_size`: Calculate required N
        - `power`: Calculate achieved power given N
        - `effect_size`: Calculate w from contingency table

        **Effect Size (Cramér's w or Cohen's w):**
        - 0.10 = small, 0.30 = medium, 0.50 = large

        Args:
            effect_size: Cohen's w (or calculate from observed table)
            df: Degrees of freedom = (rows-1) * (cols-1)
            mode: "sample_size" | "power" | "effect_size"
            n: Total sample size (for power mode)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            observed: Contingency table as 2D list (for effect_size mode)

        Returns:
            Mode-specific results

        Examples:
            # 2x2 table, medium effect
            power_chisquare(effect_size=0.30, df=1, mode="sample_size")

            # Calculate effect from table
            power_chisquare(effect_size=0, df=1, mode="effect_size",
                          observed=[[50, 30], [20, 40]])
        """
        try:
            import math

            if mode == "effect_size":
                if observed:
                    # Calculate chi-square statistic
                    rows = len(observed)
                    cols = len(observed[0])
                    n_total = sum(sum(row) for row in observed)
                    row_totals = [sum(row) for row in observed]
                    col_totals = [sum(observed[r][c] for r in range(rows)) for c in range(cols)]

                    chi2 = 0
                    for r in range(rows):
                        for c in range(cols):
                            expected = row_totals[r] * col_totals[c] / n_total
                            chi2 += (observed[r][c] - expected)**2 / expected

                    w = math.sqrt(chi2 / n_total)
                    interpretation = "small" if w < 0.30 else "medium" if w < 0.50 else "large"
                    return {
                        "status": "success",
                        "effect_size_w": round(w, 4),
                        "chi_square": round(chi2, 4),
                        "interpretation": interpretation,
                        "n": n_total
                    }
                return {"status": "error", "error": "Provide observed contingency table for effect_size mode"}

            if mode == "sample_size":
                result = await stats_client.calculate_chisquare_power(
                    effect_size=effect_size, df=df, alpha=alpha, power=power, n=None
                )
                return result

            if mode == "power":
                if n is None:
                    return {"status": "error", "error": "Provide n for power calculation"}
                result = await stats_client.calculate_chisquare_power(
                    effect_size=effect_size, df=df, alpha=alpha, power=None, n=n
                )
                return result

            return {"status": "error", "error": f"Unknown mode: {mode}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def power_survival(
        hazard_ratio: float,
        mode: str = "sample_size",
        total_events: Optional[int] = None,
        total_n: Optional[int] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        dropout_rate: float = 0.0,
        median1: Optional[float] = None,
        median2: Optional[float] = None,
        accrual_time: Optional[float] = None,
        followup_time: Optional[float] = None,
    ) -> dict:
        """
        📊 Survival Analysis Power Analysis (unified tool).

        For time-to-event studies comparing survival curves.

        **Modes:**
        - `sample_size`: Calculate required N and events
        - `power`: Calculate achieved power given events
        - `events`: Calculate required events for given power
        - `from_medians`: Calculate HR and sample size from median survival times

        **Hazard Ratio:**
        - HR < 1: Treatment reduces hazard (beneficial)
        - HR > 1: Treatment increases hazard (harmful)
        - HR = 1: No effect

        Args:
            hazard_ratio: Expected hazard ratio
            mode: "sample_size" | "power" | "events" | "from_medians"
            total_events: Number of events (for power mode)
            total_n: Total sample size (for power mode)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            ratio: Allocation ratio n2/n1 (default: 1.0)
            dropout_rate: Expected dropout rate (default: 0)
            median1: Median survival time group 1 (for from_medians mode)
            median2: Median survival time group 2 (for from_medians mode)
            accrual_time: Recruitment period (for sample size)
            followup_time: Follow-up period (for sample size)

        Returns:
            Mode-specific results including events, sample size, power

        Examples:
            # HR=0.7, calculate sample size
            power_survival(hazard_ratio=0.7, mode="sample_size")

            # Calculate from median survival (12 vs 18 months)
            power_survival(hazard_ratio=0, mode="from_medians",
                          median1=12, median2=18)

            # Check power with 200 events
            power_survival(hazard_ratio=0.7, mode="power", total_events=200)
        """
        try:
            import math

            # Mode: from_medians
            if mode == "from_medians":
                if median1 and median2:
                    hr = median1 / median2  # HR = median_control / median_treatment
                    log_hr = math.log(hr)
                    return {
                        "status": "success",
                        "hazard_ratio": round(hr, 4),
                        "log_hazard_ratio": round(log_hr, 4),
                        "median1": median1,
                        "median2": median2,
                        "interpretation": f"HR={round(hr, 2)} means {'treatment beneficial' if hr < 1 else 'treatment harmful' if hr > 1 else 'no effect'}",
                        "recommendation": f"Use hazard_ratio={round(hr, 2)} for power analysis"
                    }
                return {"status": "error", "error": "Provide median1 and median2 for from_medians mode"}

            # Mode: events calculation
            if mode == "events":
                result = await stats_client.calculate_survival_events(
                    hazard_ratio=hazard_ratio, alpha=alpha, power=power, ratio=ratio
                )
                return result

            # Mode: sample_size
            if mode == "sample_size":
                result = await stats_client.calculate_survival_sample_size(
                    hazard_ratio=hazard_ratio, alpha=alpha, power=power,
                    ratio=ratio, dropout_rate=dropout_rate,
                    accrual_time=accrual_time, followup_time=followup_time
                )
                return result

            # Mode: power
            if mode == "power":
                if total_events is None:
                    return {"status": "error", "error": "Provide total_events for power calculation"}
                result = await stats_client.calculate_survival_power(
                    hazard_ratio=hazard_ratio, total_events=total_events,
                    alpha=alpha, ratio=ratio
                )
                return result

            return {"status": "error", "error": f"Unknown mode: {mode}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    logger.info("Power analysis tools registered: power_ttest, power_proportion, power_anova, power_chisquare, power_survival")

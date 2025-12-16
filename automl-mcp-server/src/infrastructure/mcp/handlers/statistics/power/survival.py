"""
Survival Analysis Power Tools

Tools:
    - calculate_survival_events
    - calculate_survival_sample_size
    - calculate_survival_power
    - calculate_survival_from_medians
    - convert_hazard_ratio_to_log
"""
import math
from typing import Any, Dict, Optional

from ..base import logger


def register_survival_power_tools(mcp, stats_client):
    """Register survival analysis power tools."""

    @mcp.tool()
    async def calculate_survival_events(
        hazard_ratio: float,
        alpha: float = 0.05,
        power: float = 0.80,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Calculate required number of events for log-rank test.

        Args:
            hazard_ratio: Expected hazard ratio (treatment/control)
                - HR < 1: Treatment reduces hazard (beneficial)
                - HR > 1: Treatment increases hazard
                - HR = 0.7 means 30% reduction in hazard
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"

        Returns:
            total_events: Total required events
            events_per_group: Events in each arm
            log_hazard_ratio: log(HR) used in calculation

        Example:
            calculate_survival_events(hazard_ratio=0.7, power=0.80)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_survival_power(
                calculation_type="events",
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=power,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_survival_events error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_survival_sample_size(
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
        Calculate sample size for survival analysis (log-rank test).

        Args:
            hazard_ratio: Expected hazard ratio (treatment/control)
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            prob_event: Expected proportion observing event (default: 0.70)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"
            accrual_time: Enrollment period in months (optional)
            follow_up_time: Follow-up period after enrollment (optional)

        Returns:
            total_n: Total sample size needed
            n_treatment: Sample size for treatment group
            n_control: Sample size for control group
            total_events: Expected number of events

        Example:
            calculate_survival_sample_size(hazard_ratio=0.65, prob_event=0.70)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_survival_power(
                calculation_type="sample_size",
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=power,
                prob_event=prob_event,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
                accrual_time=accrual_time,
                follow_up_time=follow_up_time,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_survival_sample_size error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_survival_power(
        hazard_ratio: float,
        n_events: Optional[int] = None,
        total_n: Optional[int] = None,
        alpha: float = 0.05,
        prob_event: float = 0.70,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Calculate power for survival analysis given sample/events.

        Args:
            hazard_ratio: Expected hazard ratio to detect
            n_events: Number of events (directly specify events)
            total_n: Total sample size (alternative to n_events)
            alpha: Significance level (default: 0.05)
            prob_event: Event probability (used with total_n)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"

        Returns:
            power: Calculated statistical power
            n_events: Number of events used
            events_for_80pct: Events needed for 80% power

        Example:
            calculate_survival_power(hazard_ratio=0.75, n_events=200)
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_survival_power(
                calculation_type="power",
                hazard_ratio=hazard_ratio,
                n_events=n_events,
                total_n=total_n,
                alpha=alpha,
                prob_event=prob_event,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_survival_power error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def calculate_survival_from_medians(
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
        Calculate sample size from median survival times.

        Most intuitive method when you know expected median survival.

        Args:
            median_control: Expected median survival in control (months)
            median_treatment: Expected median survival in treatment (months)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            accrual_time: Enrollment period in months (default: 12)
            follow_up_time: Additional follow-up in months (default: 12)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"

        Returns:
            total_n: Total sample size
            implied_hazard_ratio: HR calculated from medians
            total_events: Required events
            study_duration: Total study duration

        Example:
            calculate_survival_from_medians(
                median_control=8,
                median_treatment=12,
                accrual_time=18,
                follow_up_time=12
            )
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.calculate_survival_power(
                calculation_type="from_medians",
                median_control=median_control,
                median_treatment=median_treatment,
                alpha=alpha,
                power=power,
                accrual_time=accrual_time,
                follow_up_time=follow_up_time,
                allocation_ratio=allocation_ratio,
                alternative=alternative,
            )
            return result
        except Exception as e:
            logger.error(f"calculate_survival_from_medians error: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def convert_hazard_ratio_to_log(
        hazard_ratio: float,
    ) -> Dict[str, Any]:
        """
        Convert hazard ratio to log hazard ratio.

        Args:
            hazard_ratio: The hazard ratio to convert

        Returns:
            hazard_ratio: Original HR
            log_hazard_ratio: log(HR)
            interpretation: Plain language explanation

        Example:
            convert_hazard_ratio_to_log(0.7)  # 30% reduction
        """
        try:
            log_hr = math.log(hazard_ratio)

            if hazard_ratio < 1:
                reduction = (1 - hazard_ratio) * 100
                interp = f"{reduction:.1f}% reduction in hazard (beneficial)"
            elif hazard_ratio > 1:
                increase = (hazard_ratio - 1) * 100
                interp = f"{increase:.1f}% increase in hazard"
            else:
                interp = "No effect"

            return {
                "hazard_ratio": hazard_ratio,
                "log_hazard_ratio": round(log_hr, 4),
                "interpretation": interp,
            }
        except Exception as e:
            logger.error(f"convert_hazard_ratio_to_log error: {e}")
            return {"status": "error", "error": str(e)}

    logger.info("Survival power tools registered: 5 tools")

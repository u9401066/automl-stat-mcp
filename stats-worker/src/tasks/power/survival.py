"""
Survival Analysis Power Module

Power analysis for survival analysis (time-to-event data).

Contains:
    - SurvivalPowerResult: Result dataclass for survival power calculations
    - SurvivalPowerAnalysis: Main analysis class using Schoenfeld formula
    - Helper functions for hazard ratio and event calculations
    - Convenience wrapper functions for MCP tools
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scipy import stats

from .base import safe_round

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions for Survival Analysis
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


# =============================================================================
# Result Dataclass
# =============================================================================


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


# =============================================================================
# Survival Power Analysis Class
# =============================================================================


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
        d = ((z_alpha + z_beta) ** 2) * ((1 + r) ** 2) / (r * (log_hr**2))
        n_events = int(math.ceil(d))

        # Events per group (assuming equal event rates)
        events_control = int(math.ceil(n_events / (1 + r)))
        n_events - events_control

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
            f"with {power * 100:.0f}% power at α = {alpha}, "
            f"you need to observe {n_events} events total."
        )

        recs = []
        if n_events > 500:
            recs.append(
                f"Large number of events ({n_events}) required. Consider longer follow-up or higher-risk population."
            )
        recs.append(
            f"With {int((1 - power) * 100)}% of events censored, total N ≈ {int(n_events / 0.7)} (assuming 70% event rate)."
        )
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
        if n_events is None:
            raise ValueError("Failed to calculate required events")

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
            f"with {power * 100:.0f}% power at α = {alpha}, assuming {prob_event * 100:.0f}% event rate, "
            f"you need N = {total_n} ({n_control} control + {n_treatment} treatment)."
        )

        recs = events_result.recommendations.copy()
        if prob_event < 0.5:
            recs.append(f"Low event rate ({prob_event * 100:.0f}%) increases sample size. Consider longer follow-up.")

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
        z_beta = math.sqrt(n_events * r * (log_hr**2) / ((1 + r) ** 2)) - z_alpha
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
            f"the study has {power * 100:.1f}% power at α = {alpha}."
        )

        recs = []
        if power < 0.80:
            needed = SurvivalPowerAnalysis.calculate_events(
                hazard_ratio=hazard_ratio,
                alpha=alpha,
                power=0.80,
                allocation_ratio=r,
                alternative=alternative,
                _include_sensitivity=False,
            )
            recs.append(f"Power is {power * 100:.1f}%. Need {needed.n_events} events for 80% power.")

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
            SurvivalPowerResult with sample size and hazard ratio
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
        result.notes.append("Based on exponential survival assumption")
        result.notes.append(f"Estimated event rate: {prob_event * 100:.0f}% over {total_time} months")

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
            by_power.append(
                {
                    "power": pwr,
                    "n_events": result.n_events,
                }
            )

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
                by_hr.append(
                    {
                        "hazard_ratio": hr,
                        "n_events": result.n_events,
                    }
                )
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
            by_prob.append(
                {
                    "prob_event": prob,
                    "total_n": result.total_n,
                    "n_events": result.n_events,
                }
            )

        return {
            "by_event_probability": by_prob,
        }


# =============================================================================
# Convenience Functions for MCP
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

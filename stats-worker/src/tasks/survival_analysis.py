"""
Survival Analysis Module

Provides survival analysis capabilities for medical research:
- Kaplan-Meier survival estimation
- Log-rank test for group comparisons
- Cox proportional hazards regression
- Hazard ratios with confidence intervals
- Survival curve data for visualization

Suitable for:
- Time-to-event analysis
- Clinical trial endpoints
- Treatment comparison studies
"""
import logging
import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore', category=RuntimeWarning)

# Optional visualization support
try:
    from src.visualization.storage import save_figure_to_minio
    from src.visualization.survival import (
        plot_cumulative_hazard,
        plot_forest_plot,
        plot_kaplan_meier,
    )
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False
    logger.debug("Visualization module not available")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert to float, handling None/NaN/inf."""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def safe_round(value: Optional[float], decimals: int = 4) -> Optional[float]:
    """Safely round a value."""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class SurvivalPoint:
    """A single point on a survival curve."""
    time: float
    survival: float
    survival_ci_lower: float
    survival_ci_upper: float
    at_risk: int
    events: int
    censored: int
    std_error: Optional[float] = None


@dataclass
class KaplanMeierResult:
    """Result of Kaplan-Meier estimation."""
    group_name: str
    n_subjects: int
    n_events: int
    n_censored: int
    median_survival: Optional[float]
    median_ci_lower: Optional[float]
    median_ci_upper: Optional[float]

    # Time points
    survival_table: List[SurvivalPoint] = field(default_factory=list)

    # Summary statistics
    mean_survival: Optional[float] = None
    restricted_mean: Optional[float] = None  # RMST

    def to_dict(self) -> Dict:
        return {
            "group": self.group_name,
            "n_subjects": self.n_subjects,
            "n_events": self.n_events,
            "n_censored": self.n_censored,
            "median_survival": safe_round(self.median_survival, 2),
            "median_ci": {
                "lower": safe_round(self.median_ci_lower, 2),
                "upper": safe_round(self.median_ci_upper, 2),
            },
            "mean_survival": safe_round(self.mean_survival, 2),
            "restricted_mean": safe_round(self.restricted_mean, 2),
            "survival_curve": [
                {
                    "time": safe_round(p.time, 2),
                    "survival": safe_round(p.survival, 4),
                    "ci_lower": safe_round(p.survival_ci_lower, 4),
                    "ci_upper": safe_round(p.survival_ci_upper, 4),
                    "at_risk": p.at_risk,
                    "events": p.events,
                    "censored": p.censored,
                }
                for p in self.survival_table
            ],
        }

    def get_survival_at_time(self, t: float) -> Tuple[float, float, float]:
        """Get survival probability at a specific time."""
        for i, point in enumerate(self.survival_table):
            if point.time > t:
                if i == 0:
                    return 1.0, 1.0, 1.0
                prev = self.survival_table[i-1]
                return prev.survival, prev.survival_ci_lower, prev.survival_ci_upper
        if self.survival_table:
            last = self.survival_table[-1]
            return last.survival, last.survival_ci_lower, last.survival_ci_upper
        return 1.0, 1.0, 1.0


@dataclass
class LogRankResult:
    """Result of log-rank test."""
    groups: List[str]
    test_statistic: float
    degrees_of_freedom: int
    p_value: float

    # Optional: pairwise comparisons
    pairwise: Optional[Dict[str, Dict]] = None

    def to_dict(self) -> Dict:
        result: Dict[str, Any] = {
            "groups": self.groups,
            "test_statistic": safe_round(self.test_statistic, 3),
            "degrees_of_freedom": self.degrees_of_freedom,
            "p_value": safe_round(self.p_value, 4),
            "significant": self.p_value < 0.05,
        }
        if self.pairwise:
            result["pairwise_comparisons"] = self.pairwise
        return result


@dataclass
class CoxCoefficient:
    """A single coefficient from Cox regression."""
    variable: str
    coefficient: float
    std_error: float
    hazard_ratio: float
    hr_ci_lower: float
    hr_ci_upper: float
    z_score: float
    p_value: float

    def to_dict(self) -> Dict:
        return {
            "variable": self.variable,
            "coefficient": safe_round(self.coefficient, 4),
            "std_error": safe_round(self.std_error, 4),
            "hazard_ratio": safe_round(self.hazard_ratio, 3),
            "hr_ci": {
                "lower": safe_round(self.hr_ci_lower, 3),
                "upper": safe_round(self.hr_ci_upper, 3),
            },
            "z_score": safe_round(self.z_score, 3),
            "p_value": safe_round(self.p_value, 4),
            "significant": self.p_value < 0.05,
        }


@dataclass
class CoxRegressionResult:
    """Result of Cox proportional hazards regression."""
    n_subjects: int
    n_events: int

    coefficients: List[CoxCoefficient] = field(default_factory=list)

    # Model fit statistics
    log_likelihood: Optional[float] = None
    log_likelihood_null: Optional[float] = None
    concordance: Optional[float] = None

    # Global tests
    likelihood_ratio_test: Optional[float] = None
    likelihood_ratio_pvalue: Optional[float] = None
    wald_test: Optional[float] = None
    wald_pvalue: Optional[float] = None

    # Diagnostics
    proportional_hazards_test: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "n_subjects": self.n_subjects,
            "n_events": self.n_events,
            "coefficients": [c.to_dict() for c in self.coefficients],
            "model_fit": {
                "log_likelihood": safe_round(self.log_likelihood, 2),
                "log_likelihood_null": safe_round(self.log_likelihood_null, 2),
                "concordance": safe_round(self.concordance, 3),
            },
            "global_tests": {
                "likelihood_ratio": {
                    "statistic": safe_round(self.likelihood_ratio_test, 3),
                    "p_value": safe_round(self.likelihood_ratio_pvalue, 4),
                },
                "wald": {
                    "statistic": safe_round(self.wald_test, 3),
                    "p_value": safe_round(self.wald_pvalue, 4),
                },
            },
            "proportional_hazards_test": self.proportional_hazards_test,
        }


# =============================================================================
# Kaplan-Meier Estimator
# =============================================================================

class KaplanMeierEstimator:
    """
    Kaplan-Meier survival curve estimator.

    The Kaplan-Meier estimator is a non-parametric statistic used to
    estimate the survival function from lifetime data. It is also known
    as the product-limit estimator.

    Usage:
        km = KaplanMeierEstimator()
        result = km.fit(times, events)

        # With groups
        results = km.fit_groups(times, events, groups)
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize estimator.

        Args:
            alpha: Significance level for confidence intervals (default: 0.05 for 95% CI)
        """
        self.alpha = alpha
        self.z_alpha = stats.norm.ppf(1 - alpha/2)

    def fit(
        self,
        times: np.ndarray,
        events: np.ndarray,
        group_name: str = "Overall",
    ) -> KaplanMeierResult:
        """
        Fit Kaplan-Meier estimator.

        Args:
            times: Array of survival/follow-up times
            events: Array of event indicators (1=event, 0=censored)
            group_name: Name for this group

        Returns:
            KaplanMeierResult with survival curve data
        """
        times = np.asarray(times, dtype=float)
        events = np.asarray(events, dtype=int)

        # Remove NaN
        valid = ~(np.isnan(times) | np.isnan(events))
        times = times[valid]
        events = events[valid]

        n_subjects = len(times)
        n_events = int(events.sum())
        n_censored = n_subjects - n_events

        if n_subjects == 0:
            return KaplanMeierResult(
                group_name=group_name,
                n_subjects=0,
                n_events=0,
                n_censored=0,
                median_survival=None,
                median_ci_lower=None,
                median_ci_upper=None,
            )

        # Sort by time
        order = np.argsort(times)
        times = times[order]
        events = events[order]

        # Get unique event times
        unique_times = np.unique(times[events == 1])

        survival_points = []
        survival = 1.0
        variance_sum = 0.0  # Greenwood's formula

        # Add time 0
        survival_points.append(SurvivalPoint(
            time=0.0,
            survival=1.0,
            survival_ci_lower=1.0,
            survival_ci_upper=1.0,
            at_risk=n_subjects,
            events=0,
            censored=0,
            std_error=0.0,
        ))

        for t in unique_times:
            # Number at risk just before time t
            at_risk = np.sum(times >= t)

            # Number of events at time t
            d = np.sum((times == t) & (events == 1))

            # Number censored at time t
            c = np.sum((times == t) & (events == 0))

            if at_risk > 0:
                # Kaplan-Meier product
                survival *= (1 - d / at_risk)

                # Greenwood's formula for variance
                if at_risk > d:
                    variance_sum += d / (at_risk * (at_risk - d))

            # Standard error and CI (log-log transformation)
            if survival > 0 and survival < 1 and variance_sum > 0:
                std_error = survival * np.sqrt(variance_sum)

                # Log-log CI (more stable near 0 and 1)
                log_log_se = np.sqrt(variance_sum) / np.abs(np.log(survival))
                ci_lower = survival ** np.exp(self.z_alpha * log_log_se)
                ci_upper = survival ** np.exp(-self.z_alpha * log_log_se)
            else:
                std_error = 0.0
                ci_lower = survival
                ci_upper = survival

            survival_points.append(SurvivalPoint(
                time=float(t),
                survival=float(survival),
                survival_ci_lower=float(max(0, ci_lower)),
                survival_ci_upper=float(min(1, ci_upper)),
                at_risk=int(at_risk),
                events=int(d),
                censored=int(c),
                std_error=float(std_error),
            ))

        # Calculate median survival
        median, median_ci_lower, median_ci_upper = self._calculate_median(survival_points)

        # Calculate restricted mean survival time (RMST)
        rmst = self._calculate_rmst(survival_points, max(times))

        return KaplanMeierResult(
            group_name=group_name,
            n_subjects=n_subjects,
            n_events=n_events,
            n_censored=n_censored,
            median_survival=median,
            median_ci_lower=median_ci_lower,
            median_ci_upper=median_ci_upper,
            survival_table=survival_points,
            restricted_mean=rmst,
        )

    def fit_groups(
        self,
        times: np.ndarray,
        events: np.ndarray,
        groups: np.ndarray,
    ) -> Dict[str, KaplanMeierResult]:
        """
        Fit Kaplan-Meier estimator for multiple groups.

        Args:
            times: Array of survival/follow-up times
            events: Array of event indicators
            groups: Array of group labels

        Returns:
            Dictionary mapping group names to KaplanMeierResult
        """
        times = np.asarray(times)
        events = np.asarray(events)
        groups = np.asarray(groups)

        results = {}
        for group in np.unique(groups):
            mask = groups == group
            results[str(group)] = self.fit(
                times[mask],
                events[mask],
                group_name=str(group),
            )

        return results

    def _calculate_median(
        self,
        survival_points: List[SurvivalPoint],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate median survival time with CI."""
        if not survival_points:
            return None, None, None

        median = None
        median_ci_lower = None
        median_ci_upper = None

        for _i, point in enumerate(survival_points):
            if point.survival <= 0.5:
                median = point.time

                # Find CI bounds
                for p in survival_points:
                    if p.survival_ci_upper <= 0.5 and median_ci_lower is None:
                        median_ci_lower = p.time
                    if p.survival_ci_lower <= 0.5 and median_ci_upper is None:
                        median_ci_upper = p.time
                break

        return median, median_ci_lower, median_ci_upper

    def _calculate_rmst(
        self,
        survival_points: List[SurvivalPoint],
        max_time: float,
    ) -> float:
        """Calculate restricted mean survival time (area under KM curve)."""
        if len(survival_points) < 2:
            return 0.0

        rmst = 0.0
        for i in range(len(survival_points) - 1):
            t1 = survival_points[i].time
            t2 = survival_points[i + 1].time
            s = survival_points[i].survival

            # Area of rectangle
            rmst += s * (t2 - t1)

        return rmst


# =============================================================================
# Log-Rank Test
# =============================================================================

def log_rank_test(
    times: np.ndarray,
    events: np.ndarray,
    groups: np.ndarray,
    pairwise: bool = False,
) -> LogRankResult:
    """
    Perform log-rank test comparing survival curves.

    The log-rank test is used to test the null hypothesis that there is
    no difference between the survival curves of different groups.

    Args:
        times: Array of survival/follow-up times
        events: Array of event indicators (1=event, 0=censored)
        groups: Array of group labels
        pairwise: If True, perform pairwise comparisons for >2 groups

    Returns:
        LogRankResult with test statistic and p-value
    """
    times = np.asarray(times, dtype=float)
    events = np.asarray(events, dtype=int)
    groups = np.asarray(groups)

    # Remove NaN
    valid = ~(np.isnan(times) | np.isnan(events))
    times = times[valid]
    events = events[valid]
    groups = groups[valid]

    unique_groups = np.unique(groups)
    n_groups = len(unique_groups)

    if n_groups < 2:
        return LogRankResult(
            groups=list(unique_groups),
            test_statistic=0.0,
            degrees_of_freedom=0,
            p_value=1.0,
        )

    # Get all unique event times
    event_times = np.unique(times[events == 1])

    # Calculate observed and expected events per group
    observed_events = np.zeros(n_groups)  # Observed
    expected_events = np.zeros(n_groups)  # Expected
    variance_matrix = np.zeros((n_groups, n_groups))  # Variance-covariance matrix

    for t in event_times:
        # Total at risk and events at this time
        at_risk_total = np.sum(times >= t)
        events_total = np.sum((times == t) & (events == 1))

        if at_risk_total == 0:
            continue

        for i, g in enumerate(unique_groups):
            mask = groups == g
            at_risk_g = np.sum(times[mask] >= t)
            events_g = np.sum((times[mask] == t) & (events[mask] == 1))

            observed_events[i] += events_g
            expected_events[i] += at_risk_g * events_total / at_risk_total

            # Variance contribution
            if at_risk_total > 1:
                variance_matrix[i, i] += (at_risk_g * (at_risk_total - at_risk_g) *
                           events_total * (at_risk_total - events_total) /
                           (at_risk_total ** 2 * (at_risk_total - 1)))

                for j in range(i + 1, n_groups):
                    mask_j = groups == unique_groups[j]
                    at_risk_j = np.sum(times[mask_j] >= t)

                    variance_matrix[i, j] -= (at_risk_g * at_risk_j *
                               events_total * (at_risk_total - events_total) /
                               (at_risk_total ** 2 * (at_risk_total - 1)))
                    variance_matrix[j, i] = variance_matrix[i, j]

    # Test statistic (use first n-1 groups due to linear dependency)
    diff = (observed_events - expected_events)[:-1]
    V_reduced = variance_matrix[:-1, :-1]

    try:
        V_inv = np.linalg.pinv(V_reduced)
        chi2 = float(diff @ V_inv @ diff)
    except Exception:
        chi2 = float(np.sum((observed_events - expected_events) ** 2 / np.maximum(expected_events, 1e-10)))

    df = n_groups - 1
    p_value = float(1 - stats.chi2.cdf(chi2, df))

    result = LogRankResult(
        groups=[str(g) for g in unique_groups],
        test_statistic=chi2,
        degrees_of_freedom=df,
        p_value=p_value,
    )

    # Pairwise comparisons if requested and >2 groups
    if pairwise and n_groups > 2:
        pairwise_results = {}
        for i, g1 in enumerate(unique_groups):
            for j, g2 in enumerate(unique_groups):
                if i < j:
                    pair_mask = (groups == g1) | (groups == g2)
                    pair_result = log_rank_test(
                        times[pair_mask],
                        events[pair_mask],
                        groups[pair_mask],
                        pairwise=False,
                    )
                    key = f"{g1} vs {g2}"
                    pairwise_results[key] = {
                        "statistic": safe_round(pair_result.test_statistic, 3),
                        "p_value": safe_round(pair_result.p_value, 4),
                        # Bonferroni correction
                        "p_value_adjusted": safe_round(
                            min(1.0, pair_result.p_value * (n_groups * (n_groups - 1) / 2)),
                            4
                        ),
                    }
        result.pairwise = pairwise_results

    return result


# =============================================================================
# Cox Proportional Hazards Regression
# =============================================================================

class CoxPHFitter:
    """
    Cox Proportional Hazards regression model.

    The Cox model is a semi-parametric survival model that assumes
    hazards are proportional over time.

    h(t|X) = h0(t) * exp(β'X)

    Usage:
        cox = CoxPHFitter()
        result = cox.fit(df, duration_col='time', event_col='event',
                        covariates=['age', 'treatment'])
    """

    def __init__(self, alpha: float = 0.05, max_iter: int = 100, tol: float = 1e-9):
        """
        Initialize Cox model.

        Args:
            alpha: Significance level for confidence intervals
            max_iter: Maximum iterations for optimization
            tol: Tolerance for convergence
        """
        self.alpha = alpha
        self.z_alpha = stats.norm.ppf(1 - alpha/2)
        self.max_iter = max_iter
        self.tol = tol

    def fit(
        self,
        df: pd.DataFrame,
        duration_col: str,
        event_col: str,
        covariates: Optional[List[str]] = None,
    ) -> CoxRegressionResult:
        """
        Fit Cox proportional hazards model.

        Args:
            df: DataFrame with survival data
            duration_col: Column name for duration/time
            event_col: Column name for event indicator
            covariates: List of covariate column names (default: all numeric)

        Returns:
            CoxRegressionResult with coefficients and hazard ratios
        """
        # Prepare data
        df = df.copy()

        # Handle covariates
        if covariates is None:
            covariates = [c for c in df.select_dtypes(include=[np.number]).columns
                         if c not in [duration_col, event_col]]

        # Remove rows with missing values
        cols = [duration_col, event_col] + covariates
        df = df[cols].dropna()

        times = df[duration_col].values.astype(float)
        events = df[event_col].values.astype(int)
        X = df[covariates].values.astype(float)

        n_subjects = len(times)
        n_events: int = int(events.sum())
        n_features = len(covariates)

        if n_subjects < 2 or n_events < 1 or n_features < 1:
            return CoxRegressionResult(
                n_subjects=n_subjects,
                n_events=n_events,
            )

        # Standardize covariates for numerical stability
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1  # Prevent division by zero
        X_norm = (X - X_mean) / X_std

        # Sort by time
        order = np.argsort(times)
        times = times[order]
        events = events[order]
        X_norm = X_norm[order]

        # Initial coefficients
        beta = np.zeros(n_features)

        # Newton-Raphson optimization
        for _iteration in range(self.max_iter):
            # Calculate risk scores
            risk = np.exp(X_norm @ beta)

            # Partial likelihood derivatives
            gradient = np.zeros(n_features)
            hessian = np.zeros((n_features, n_features))

            log_likelihood = 0.0

            for i in range(n_subjects):
                if events[i] == 0:
                    continue

                # Risk set (all subjects still at risk at time i)
                at_risk = times >= times[i]
                risk_sum = risk[at_risk].sum()

                if risk_sum == 0:
                    continue

                # Weighted mean of covariates
                X_risk = X_norm[at_risk]
                weights = risk[at_risk] / risk_sum
                X_bar = (X_risk.T @ weights)

                # Gradient
                gradient += X_norm[i] - X_bar

                # Hessian
                X_outer = (X_risk.T * weights) @ X_risk
                hessian -= X_outer - np.outer(X_bar, X_bar)

                # Log-likelihood
                log_likelihood += X_norm[i] @ beta - np.log(risk_sum)

            # Newton step
            try:
                step = np.linalg.solve(-hessian, gradient)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(-hessian, gradient, rcond=None)[0]

            beta_new = beta + step

            # Check convergence
            if np.max(np.abs(step)) < self.tol:
                beta = beta_new
                break

            beta = beta_new

        # Transform coefficients back to original scale
        beta_original = beta / X_std

        # Calculate standard errors
        try:
            cov_matrix = -np.linalg.inv(hessian)
            se_norm = np.sqrt(np.diag(cov_matrix))
            se_original = se_norm / X_std
        except Exception:
            se_original = np.ones(n_features) * np.nan

        # Build coefficient results
        coefficients = []
        for i, var in enumerate(covariates):
            coef = beta_original[i]
            se = se_original[i]
            hr = np.exp(coef)

            if not np.isnan(se):
                z = coef / se
                p_value = 2 * (1 - stats.norm.cdf(abs(z)))
                hr_lower = np.exp(coef - self.z_alpha * se)
                hr_upper = np.exp(coef + self.z_alpha * se)
            else:
                z = np.nan
                p_value = np.nan
                hr_lower = np.nan
                hr_upper = np.nan

            coefficients.append(CoxCoefficient(
                variable=var,
                coefficient=float(coef),
                std_error=float(se),
                hazard_ratio=float(hr),
                hr_ci_lower=float(hr_lower),
                hr_ci_upper=float(hr_upper),
                z_score=float(z),
                p_value=float(p_value),
            ))

        # Calculate null model log-likelihood
        log_likelihood_null = -n_events * np.log(n_subjects)

        # Likelihood ratio test
        lr_stat = 2 * (log_likelihood - log_likelihood_null)
        lr_pvalue = 1 - stats.chi2.cdf(lr_stat, n_features)

        # Wald test
        try:
            wald_stat = float(beta @ (-hessian) @ beta)
            wald_pvalue = 1 - stats.chi2.cdf(wald_stat, n_features)
        except Exception:
            wald_stat = None
            wald_pvalue = None

        # Concordance index
        concordance = self._calculate_concordance(times, events, X_norm @ beta)

        return CoxRegressionResult(
            n_subjects=n_subjects,
            n_events=n_events,
            coefficients=coefficients,
            log_likelihood=float(log_likelihood),
            log_likelihood_null=float(log_likelihood_null),
            concordance=float(concordance) if concordance else None,
            likelihood_ratio_test=float(lr_stat),
            likelihood_ratio_pvalue=float(lr_pvalue),
            wald_test=wald_stat,
            wald_pvalue=wald_pvalue,
        )

    def _calculate_concordance(
        self,
        times: np.ndarray,
        events: np.ndarray,
        risk_scores: np.ndarray,
    ) -> Optional[float]:
        """Calculate Harrell's concordance index (C-index)."""
        try:
            n = len(times)
            concordant: float = 0.0
            discordant: float = 0.0
            tied: float = 0.0

            for i in range(n):
                if events[i] == 0:
                    continue

                for j in range(n):
                    if i == j:
                        continue
                    if times[j] < times[i]:
                        continue  # j had event/censoring before i's event

                    # Compare risk scores
                    if risk_scores[i] > risk_scores[j]:
                        concordant += 1
                    elif risk_scores[i] < risk_scores[j]:
                        discordant += 1
                    else:
                        tied += 0.5

            total = concordant + discordant + tied
            if total > 0:
                return (concordant + 0.5 * tied) / total
            return None
        except Exception:
            return None


# =============================================================================
# Convenience Functions
# =============================================================================

def kaplan_meier_analysis(
    df: pd.DataFrame,
    time_col: str,
    event_col: str,
    group_col: Optional[str] = None,
    alpha: float = 0.05,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform Kaplan-Meier survival analysis.

    Args:
        df: DataFrame with survival data
        time_col: Column name for time-to-event
        event_col: Column name for event indicator (1=event, 0=censored)
        group_col: Optional column for grouping (stratification)
        alpha: Significance level for CI (default: 0.05)
        generate_visualizations: Whether to generate KM curve plot
        user_id: User ID for MinIO storage (required if generate_visualizations=True)
        job_id: Job ID for MinIO storage (required if generate_visualizations=True)

    Returns:
        Dictionary with survival curves and statistics
    """
    km = KaplanMeierEstimator(alpha=alpha)

    times = df[time_col].values
    events = df[event_col].values

    result = {
        "analysis_type": "kaplan_meier",
        "time_column": time_col,
        "event_column": event_col,
        "alpha": alpha,
    }

    if group_col and group_col in df.columns:
        groups = df[group_col].values
        km_results = km.fit_groups(times, events, groups)

        result["grouped"] = True
        result["group_column"] = group_col
        result["groups"] = {k: v.to_dict() for k, v in km_results.items()}

        # Log-rank test
        lr = log_rank_test(times, events, groups, pairwise=True)
        result["log_rank_test"] = lr.to_dict()

        # Generate visualizations if requested
        if generate_visualizations and HAS_VISUALIZATION:
            try:
                import matplotlib.pyplot as plt

                visualizations = []
                group_data = [v.to_dict() for v in km_results.values()]

                # Kaplan-Meier curve
                fig_km = plot_kaplan_meier(
                    group_data,
                    title="Kaplan-Meier Survival Curves",
                    log_rank_p=lr.p_value,
                )
                if user_id and job_id:
                    url = save_figure_to_minio(fig_km, user_id, job_id, "kaplan_meier.png")
                    visualizations.append({
                        "type": "kaplan_meier",
                        "url": url,
                        "title": "Kaplan-Meier Survival Curves by Group",
                        "description": f"Log-rank p = {lr.p_value:.4f}",
                    })
                plt.close(fig_km)

                result["visualizations"] = visualizations

            except Exception as e:
                logger.error(f"Error generating KM visualization: {e}")
                result["visualization_error"] = str(e)
    else:
        km_result = km.fit(times, events, "Overall")
        result["grouped"] = False
        result["overall"] = km_result.to_dict()

        # Generate visualizations for single group
        if generate_visualizations and HAS_VISUALIZATION:
            try:
                import matplotlib.pyplot as plt

                visualizations = []

                # Kaplan-Meier curve
                fig_km = plot_kaplan_meier(
                    [km_result.to_dict()],
                    title="Kaplan-Meier Survival Curve",
                )
                if user_id and job_id:
                    url = save_figure_to_minio(fig_km, user_id, job_id, "kaplan_meier.png")
                    visualizations.append({
                        "type": "kaplan_meier",
                        "url": url,
                        "title": "Kaplan-Meier Survival Curve",
                        "description": "Overall survival probability over time",
                    })
                plt.close(fig_km)

                result["visualizations"] = visualizations

            except Exception as e:
                logger.error(f"Error generating KM visualization: {e}")
                result["visualization_error"] = str(e)

    return result


def cox_regression(
    df: pd.DataFrame,
    time_col: str,
    event_col: str,
    covariates: Optional[List[str]] = None,
    alpha: float = 0.05,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform Cox proportional hazards regression.

    Args:
        df: DataFrame with survival data
        time_col: Column name for time-to-event
        event_col: Column name for event indicator
        covariates: List of covariate column names
        alpha: Significance level for CI
        generate_visualizations: Whether to generate forest plot
        user_id: User ID for MinIO storage
        job_id: Job ID for MinIO storage

    Returns:
        Dictionary with regression results and optional visualizations
    """
    cox = CoxPHFitter(alpha=alpha)
    result = cox.fit(df, time_col, event_col, covariates)

    output = {
        "analysis_type": "cox_regression",
        "time_column": time_col,
        "event_column": event_col,
        "covariates": covariates,
        "alpha": alpha,
        **result.to_dict(),
    }

    # Generate forest plot if requested
    if generate_visualizations and HAS_VISUALIZATION:
        try:
            import matplotlib.pyplot as plt

            visualizations = []

            fig_forest = plot_forest_plot(result.to_dict())
            if user_id and job_id:
                url = save_figure_to_minio(fig_forest, user_id, job_id, "forest_plot.png")
                visualizations.append({
                    "type": "forest_plot",
                    "url": url,
                    "title": "Forest Plot - Cox Regression",
                    "description": "Hazard ratios with 95% confidence intervals",
                    "metadata": {
                        "n_subjects": result.n_subjects,
                        "n_events": result.n_events,
                        "concordance": result.concordance,
                    }
                })
            plt.close(fig_forest)

            output["visualizations"] = visualizations

        except Exception as e:
            logger.error(f"Error generating Cox regression visualizations: {e}")
            output["visualization_error"] = str(e)

    return output


def survival_summary(
    df: pd.DataFrame,
    time_col: str,
    event_col: str,
    group_col: Optional[str] = None,
    time_points: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Get summary statistics for survival data.

    Args:
        df: DataFrame with survival data
        time_col: Column name for time-to-event
        event_col: Column name for event indicator
        group_col: Optional grouping column
        time_points: Specific times to report survival (e.g., [12, 24, 36] months)

    Returns:
        Summary statistics
    """
    km = KaplanMeierEstimator()

    times = df[time_col].values
    events = df[event_col].values

    summary: Dict[str, Any] = {
        "n_subjects": len(df),
        "n_events": int(events.sum()),
        "n_censored": int(len(df) - events.sum()),
        "follow_up": {
            "median": safe_round(np.median(times), 2),
            "mean": safe_round(np.mean(times), 2),
            "min": safe_round(np.min(times), 2),
            "max": safe_round(np.max(times), 2),
        },
    }

    if group_col and group_col in df.columns:
        groups = df[group_col].values
        unique_groups = np.unique(groups)

        group_summaries = {}
        for g in unique_groups:
            mask = groups == g
            km_result = km.fit(times[mask], events[mask], str(g))

            group_summary: Dict[str, Any] = {
                "n_subjects": int(mask.sum()),
                "n_events": int(events[mask].sum()),
                "median_survival": safe_round(km_result.median_survival, 2),
            }

            if time_points:
                group_summary["survival_at_times"] = {}
                for t in time_points:
                    s, s_lower, s_upper = km_result.get_survival_at_time(t)
                    group_summary["survival_at_times"][f"t={t}"] = {
                        "survival": safe_round(s, 3),
                        "ci_lower": safe_round(s_lower, 3),
                        "ci_upper": safe_round(s_upper, 3),
                    }

            group_summaries[str(g)] = group_summary

        summary["by_group"] = group_summaries

        # Log-rank test
        lr = log_rank_test(times, events, groups)
        summary["log_rank_p_value"] = safe_round(lr.p_value, 4)
    else:
        km_result = km.fit(times, events)
        summary["median_survival"] = safe_round(km_result.median_survival, 2)

        if time_points:
            summary["survival_at_times"] = {}
            for t in time_points:
                s, s_lower, s_upper = km_result.get_survival_at_time(t)
                summary["survival_at_times"][f"t={t}"] = {
                    "survival": safe_round(s, 3),
                    "ci_lower": safe_round(s_lower, 3),
                    "ci_upper": safe_round(s_upper, 3),
                }

    return summary


def compare_survival_curves(
    df: pd.DataFrame,
    time_col: str,
    event_col: str,
    group_col: str,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare survival curves between groups.

    Args:
        df: DataFrame with survival data
        time_col: Column name for time-to-event
        event_col: Column name for event indicator
        group_col: Column for grouping
        generate_visualizations: Whether to generate plot images
        user_id: User ID for MinIO storage (required if generate_visualizations=True)
        job_id: Job ID for MinIO storage (required if generate_visualizations=True)

    Returns:
        Comparison results with log-rank test and optional visualizations
    """
    times = df[time_col].values
    events = df[event_col].values
    groups = df[group_col].values

    # Kaplan-Meier for each group
    km = KaplanMeierEstimator()
    km_results = km.fit_groups(times, events, groups)

    # Log-rank test
    lr = log_rank_test(times, events, groups, pairwise=True)

    result: Dict[str, Any] = {
        "comparison_type": "survival_curves",
        "groups": {k: v.to_dict() for k, v in km_results.items()},
        "log_rank_test": lr.to_dict(),
        "conclusion": "Significant difference" if lr.p_value < 0.05 else "No significant difference",
    }

    # Generate visualizations if requested
    if generate_visualizations and HAS_VISUALIZATION:
        try:
            import matplotlib.pyplot as plt

            visualizations = []
            group_data = [v.to_dict() for v in km_results.values()]

            # Kaplan-Meier curve
            fig_km = plot_kaplan_meier(
                group_data,
                title="Kaplan-Meier Survival Curves",
                log_rank_p=lr.p_value,
            )
            if user_id and job_id:
                url = save_figure_to_minio(fig_km, user_id, job_id, "kaplan_meier.png")
                visualizations.append({
                    "type": "kaplan_meier",
                    "url": url,
                    "title": "Kaplan-Meier Survival Curves",
                    "description": f"Log-rank p = {lr.p_value:.4f}",
                })
            plt.close(fig_km)

            # Cumulative hazard
            fig_ch = plot_cumulative_hazard(group_data)
            if user_id and job_id:
                url = save_figure_to_minio(fig_ch, user_id, job_id, "cumulative_hazard.png")
                visualizations.append({
                    "type": "cumulative_hazard",
                    "url": url,
                    "title": "Nelson-Aalen Cumulative Hazard",
                    "description": "Cumulative hazard function by group",
                })
            plt.close(fig_ch)

            result["visualizations"] = visualizations

        except Exception as e:
            logger.error(f"Error generating survival visualizations: {e}")
            result["visualization_error"] = str(e)

    return result

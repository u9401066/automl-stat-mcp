"""
Propensity Score Analysis Module

Provides tools for causal inference using propensity score methods:
- Propensity score estimation (logistic regression)
- Propensity score matching (nearest neighbor, caliper)
- Inverse probability weighting (IPW, IPTW)
- Balance diagnostics (SMD, KS test, variance ratios)
- Treatment effect estimation (ATE, ATT, ATU)

Reference:
- Rosenbaum & Rubin (1983). The central role of the propensity score
- Austin (2011). An Introduction to Propensity Score Methods
- Stuart (2010). Matching methods for causal inference
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit  # logistic function


@dataclass
class PropensityScoreResult:
    """Result of propensity score estimation."""

    scores: np.ndarray
    treatment: np.ndarray
    coefficients: Dict[str, float]
    intercept: float
    model_metrics: Dict[str, float]
    distribution: Dict[str, Dict[str, float]]
    overlap_region: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_treated": int(np.sum(self.treatment)),
            "n_control": int(np.sum(1 - self.treatment)),
            "coefficients": self.coefficients,
            "intercept": float(self.intercept),
            "model_metrics": self.model_metrics,
            "score_distribution": {
                "treated": self.distribution["treated"],
                "control": self.distribution["control"],
            },
            "overlap_region": {
                "lower": float(self.overlap_region[0]),
                "upper": float(self.overlap_region[1]),
            },
        }


@dataclass
class MatchingResult:
    """Result of propensity score matching."""

    matched_pairs: List[Tuple[int, int]]
    matched_treated_idx: np.ndarray
    matched_control_idx: np.ndarray
    n_matched: int
    n_unmatched_treated: int
    n_unmatched_control: int
    caliper_used: Optional[float]
    matching_method: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_matched_pairs": self.n_matched,
            "n_unmatched_treated": self.n_unmatched_treated,
            "n_unmatched_control": self.n_unmatched_control,
            "matching_rate_treated": self.n_matched / (self.n_matched + self.n_unmatched_treated)
            if (self.n_matched + self.n_unmatched_treated) > 0
            else 0,
            "caliper": self.caliper_used,
            "method": self.matching_method,
        }


@dataclass
class BalanceDiagnostics:
    """Balance diagnostics after matching or weighting."""

    standardized_differences: Dict[str, float]
    variance_ratios: Dict[str, float]
    ks_statistics: Dict[str, Dict[str, float]]
    overall_balance: Dict[str, float]
    balance_achieved: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standardized_mean_differences": self.standardized_differences,
            "variance_ratios": self.variance_ratios,
            "ks_tests": self.ks_statistics,
            "summary": self.overall_balance,
            "balance_achieved": self.balance_achieved,
        }


@dataclass
class TreatmentEffectResult:
    """Treatment effect estimation result."""

    effect_type: str  # ATE, ATT, ATU
    estimate: float
    std_error: float
    ci_lower: float
    ci_upper: float
    p_value: float
    method: str
    n_treated: int
    n_control: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_type": self.effect_type,
            "estimate": float(self.estimate),
            "std_error": float(self.std_error),
            "confidence_interval": {
                "lower": float(self.ci_lower),
                "upper": float(self.ci_upper),
            },
            "p_value": float(self.p_value),
            "significant": self.p_value < 0.05,
            "method": self.method,
            "n_treated": self.n_treated,
            "n_control": self.n_control,
        }


class PropensityScoreEstimator:
    """
    Estimate propensity scores using logistic regression.

    The propensity score is the probability of receiving treatment
    given observed covariates: e(x) = P(T=1|X=x)

    Example:
        >>> estimator = PropensityScoreEstimator()
        >>> result = estimator.fit(X, treatment)
        >>> scores = result.scores
    """

    def __init__(
        self,
        max_iter: int = 100,
        tol: float = 1e-6,
        regularization: float = 0.0,
    ):
        """
        Initialize the estimator.

        Args:
            max_iter: Maximum iterations for optimization
            tol: Convergence tolerance
            regularization: L2 regularization strength (0 = no regularization)
        """
        self.max_iter = max_iter
        self.tol = tol
        self.regularization = regularization
        self.coefficients_: Optional[np.ndarray] = None
        self.intercept_: float = 0.0
        self.feature_names_: Optional[List[str]] = None

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        treatment: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> PropensityScoreResult:
        """
        Fit propensity score model.

        Args:
            X: Covariate matrix (n_samples, n_features)
            treatment: Binary treatment indicator (0/1)
            feature_names: Names of features (if X is ndarray)

        Returns:
            PropensityScoreResult with scores and model info
        """
        # Convert to numpy
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            X = X.values.astype(float)
        else:
            X = np.asarray(X, dtype=float)
            self.feature_names_ = feature_names or [f"X{i}" for i in range(X.shape[1])]

        treatment = np.asarray(treatment, dtype=float).ravel()

        # Validate
        if len(treatment) != X.shape[0]:
            raise ValueError("X and treatment must have same number of samples")
        if not np.all(np.isin(treatment, [0, 1])):
            raise ValueError("Treatment must be binary (0/1)")
        if np.sum(treatment) < 2 or np.sum(1 - treatment) < 2:
            raise ValueError("Need at least 2 samples in each treatment group")

        n_samples, n_features = X.shape

        # Standardize features for numerical stability
        X_mean = np.mean(X, axis=0)
        X_std = np.std(X, axis=0)
        X_std[X_std == 0] = 1  # Avoid division by zero
        X_scaled = (X - X_mean) / X_std

        # Add intercept
        X_aug = np.column_stack([np.ones(n_samples), X_scaled])

        # Initialize coefficients
        beta = np.zeros(n_features + 1)

        # Newton-Raphson optimization
        for _iteration in range(self.max_iter):
            # Compute probabilities
            eta = X_aug @ beta
            eta = np.clip(eta, -500, 500)  # Prevent overflow
            p = expit(eta)

            # Gradient
            gradient = X_aug.T @ (treatment - p)

            # Add regularization (except for intercept)
            if self.regularization > 0:
                gradient[1:] -= self.regularization * beta[1:]

            # Hessian (negative)
            W = p * (1 - p)
            W = np.maximum(W, 1e-10)  # Numerical stability
            H = X_aug.T @ (X_aug * W[:, np.newaxis])

            # Add regularization to Hessian
            if self.regularization > 0:
                H[1:, 1:] += self.regularization * np.eye(n_features)

            # Newton update
            try:
                delta = np.linalg.solve(H, gradient)
            except np.linalg.LinAlgError:
                delta = np.linalg.lstsq(H, gradient, rcond=None)[0]

            beta_new = beta + delta

            # Check convergence
            if np.max(np.abs(delta)) < self.tol:
                beta = beta_new
                break

            beta = beta_new

        # Store coefficients (transform back to original scale)
        self.intercept_ = beta[0] - np.sum(beta[1:] * X_mean / X_std)
        self.coefficients_ = beta[1:] / X_std

        # Compute propensity scores
        scores = expit(X @ self.coefficients_ + self.intercept_)

        # Model metrics
        log_likelihood = np.sum(treatment * np.log(scores + 1e-10) + (1 - treatment) * np.log(1 - scores + 1e-10))

        # Null model (intercept only)
        p_null = np.mean(treatment)
        ll_null = np.sum(treatment * np.log(p_null + 1e-10) + (1 - treatment) * np.log(1 - p_null + 1e-10))

        # McFadden's pseudo R²
        pseudo_r2 = 1 - (log_likelihood / ll_null)

        # AUC (c-statistic)
        auc = self._compute_auc(scores, treatment)

        # Brier score
        brier = np.mean((scores - treatment) ** 2)

        model_metrics = {
            "log_likelihood": float(log_likelihood),
            "pseudo_r2": float(pseudo_r2),
            "c_statistic": float(auc),
            "brier_score": float(brier),
            "n_iterations": _iteration + 1,
        }

        # Distribution statistics
        treated_scores = scores[treatment == 1]
        control_scores = scores[treatment == 0]

        distribution = {
            "treated": {
                "mean": float(np.mean(treated_scores)),
                "std": float(np.std(treated_scores)),
                "min": float(np.min(treated_scores)),
                "max": float(np.max(treated_scores)),
                "median": float(np.median(treated_scores)),
            },
            "control": {
                "mean": float(np.mean(control_scores)),
                "std": float(np.std(control_scores)),
                "min": float(np.min(control_scores)),
                "max": float(np.max(control_scores)),
                "median": float(np.median(control_scores)),
            },
        }

        # Overlap region
        overlap_lower = max(np.min(treated_scores), np.min(control_scores))
        overlap_upper = min(np.max(treated_scores), np.max(control_scores))

        coefficients = {name: float(coef) for name, coef in zip(self.feature_names_, self.coefficients_, strict=False)}

        return PropensityScoreResult(
            scores=scores,
            treatment=treatment,
            coefficients=coefficients,
            intercept=self.intercept_,
            model_metrics=model_metrics,
            distribution=distribution,
            overlap_region=(overlap_lower, overlap_upper),
        )

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict propensity scores for new data."""
        if self.coefficients_ is None:
            raise ValueError("Model not fitted yet")

        if isinstance(X, pd.DataFrame):
            X = X.values.astype(float)
        else:
            X = np.asarray(X, dtype=float)

        return np.asarray(expit(X @ self.coefficients_ + self.intercept_))

    def _compute_auc(self, scores: np.ndarray, treatment: np.ndarray) -> float:
        """Compute AUC (area under ROC curve) using Mann-Whitney U statistic."""
        treated_scores = scores[treatment == 1]
        control_scores = scores[treatment == 0]

        n1, n0 = len(treated_scores), len(control_scores)
        if n1 == 0 or n0 == 0:
            return 0.5

        # Mann-Whitney U
        u_stat = 0
        for t_score in treated_scores:
            u_stat += np.sum(t_score > control_scores) + 0.5 * np.sum(t_score == control_scores)

        return u_stat / (n1 * n0)


class PropensityScoreMatcher:
    """
    Match treated and control units based on propensity scores.

    Methods:
    - Nearest neighbor matching (with/without replacement)
    - Caliper matching
    - Optimal matching

    Example:
        >>> matcher = PropensityScoreMatcher(method='nearest', caliper=0.2)
        >>> result = matcher.match(scores, treatment)
        >>> matched_data = df.iloc[result.matched_treated_idx.tolist() +
        ...                        result.matched_control_idx.tolist()]
    """

    def __init__(
        self,
        method: str = "nearest",
        caliper: Optional[float] = None,
        caliper_scale: str = "std",  # 'std' or 'absolute'
        ratio: int = 1,  # k:1 matching
        replacement: bool = False,
    ):
        """
        Initialize matcher.

        Args:
            method: Matching method ('nearest', 'optimal')
            caliper: Maximum distance for a match (None = no caliper)
            caliper_scale: 'std' for caliper in std deviations, 'absolute' for raw scale
            ratio: Number of controls per treated unit
            replacement: Allow matching with replacement
        """
        self.method = method
        self.caliper = caliper
        self.caliper_scale = caliper_scale
        self.ratio = ratio
        self.replacement = replacement

    def match(
        self,
        scores: np.ndarray,
        treatment: np.ndarray,
    ) -> MatchingResult:
        """
        Perform propensity score matching.

        Args:
            scores: Propensity scores
            treatment: Binary treatment indicator

        Returns:
            MatchingResult with matched indices
        """
        scores = np.asarray(scores, dtype=float)
        treatment = np.asarray(treatment, dtype=float).ravel()

        treated_idx = np.where(treatment == 1)[0]
        control_idx = np.where(treatment == 0)[0]

        treated_scores = scores[treated_idx]
        control_scores = scores[control_idx]

        # Compute caliper if using std scale
        if self.caliper is not None and self.caliper_scale == "std":
            caliper_abs = self.caliper * np.std(scores)
        else:
            caliper_abs = self.caliper

        # Perform matching
        if self.method == "nearest":
            matched_pairs = self._nearest_neighbor_match(
                treated_idx, control_idx, treated_scores, control_scores, caliper_abs
            )
        elif self.method == "optimal":
            matched_pairs = self._optimal_match(treated_idx, control_idx, treated_scores, control_scores, caliper_abs)
        else:
            raise ValueError(f"Unknown method: {self.method}")

        # Extract matched indices
        matched_treated = np.asarray([p[0] for p in matched_pairs], dtype=int)
        matched_control = np.asarray([p[1] for p in matched_pairs], dtype=int)

        # Unmatched counts
        unmatched_treated = len(treated_idx) - len(np.unique(matched_treated))
        unmatched_control = len(control_idx) - len(np.unique(matched_control))

        return MatchingResult(
            matched_pairs=matched_pairs,
            matched_treated_idx=matched_treated,
            matched_control_idx=matched_control,
            n_matched=len(matched_pairs),
            n_unmatched_treated=unmatched_treated,
            n_unmatched_control=unmatched_control,
            caliper_used=caliper_abs,
            matching_method=self.method,
        )

    def _nearest_neighbor_match(
        self,
        treated_idx: np.ndarray,
        control_idx: np.ndarray,
        treated_scores: np.ndarray,
        control_scores: np.ndarray,
        caliper: Optional[float],
    ) -> List[Tuple[int, int]]:
        """Nearest neighbor matching (greedy)."""
        matched_pairs = []
        available_controls = set(range(len(control_idx)))

        # Random order to reduce bias
        order = np.random.permutation(len(treated_idx))

        for i in order:
            if not available_controls:
                break

            t_score = treated_scores[i]
            t_idx = treated_idx[i]

            # Find nearest available control
            best_match = None
            best_distance = float("inf")

            for j in available_controls:
                distance = abs(t_score - control_scores[j])
                if distance < best_distance:
                    if caliper is None or distance <= caliper:
                        best_distance = distance
                        best_match = j

            if best_match is not None:
                matched_pairs.append((t_idx, control_idx[best_match]))
                if not self.replacement:
                    available_controls.remove(best_match)

        return matched_pairs

    def _optimal_match(
        self,
        treated_idx: np.ndarray,
        control_idx: np.ndarray,
        treated_scores: np.ndarray,
        control_scores: np.ndarray,
        caliper: Optional[float],
    ) -> List[Tuple[int, int]]:
        """
        Optimal matching using Hungarian algorithm approximation.
        For large datasets, falls back to greedy matching.
        """
        n_treated = len(treated_idx)
        n_control = len(control_idx)

        # For very large problems, use greedy
        if n_treated * n_control > 1_000_000:
            return self._nearest_neighbor_match(treated_idx, control_idx, treated_scores, control_scores, caliper)

        # Build distance matrix
        distances = np.abs(treated_scores[:, np.newaxis] - control_scores)

        # Apply caliper
        if caliper is not None:
            distances[distances > caliper] = 1e10

        # Greedy optimal: sort all pairs by distance
        pairs = []
        for i in range(n_treated):
            for j in range(n_control):
                if distances[i, j] < 1e10:
                    pairs.append((distances[i, j], i, j))

        pairs.sort(key=lambda x: x[0])

        matched_pairs = []
        used_treated = set()
        used_control = set()

        for _dist, i, j in pairs:
            if i not in used_treated and (self.replacement or j not in used_control):
                matched_pairs.append((treated_idx[i], control_idx[j]))
                used_treated.add(i)
                if not self.replacement:
                    used_control.add(j)

        return matched_pairs


class IPWeighting:
    """
    Inverse Probability Weighting for treatment effect estimation.

    Implements:
    - IPW (Inverse Probability Weighting)
    - IPTW (Inverse Probability of Treatment Weighting)
    - Stabilized weights
    - Trimmed weights

    Example:
        >>> ipw = IPWeighting(method='iptw', stabilized=True)
        >>> result = ipw.estimate_ate(outcome, treatment, scores)
    """

    def __init__(
        self,
        method: str = "iptw",
        stabilized: bool = True,
        trim_percentile: Optional[float] = None,  # e.g., 0.01 to trim 1% tails
        weight_cap: Optional[float] = None,  # Maximum weight value
    ):
        """
        Initialize IPW estimator.

        Args:
            method: 'iptw' or 'ipw'
            stabilized: Use stabilized weights
            trim_percentile: Trim extreme propensity scores
            weight_cap: Cap maximum weight value
        """
        self.method = method
        self.stabilized = stabilized
        self.trim_percentile = trim_percentile
        self.weight_cap = weight_cap

    def compute_weights(
        self,
        treatment: np.ndarray,
        scores: np.ndarray,
        target: str = "ate",  # 'ate', 'att', 'atu'
    ) -> np.ndarray:
        """
        Compute IPW weights.

        Args:
            treatment: Binary treatment indicator
            scores: Propensity scores
            target: Target estimand ('ate', 'att', 'atu')

        Returns:
            Array of weights
        """
        treatment = np.asarray(treatment, dtype=float)
        scores = np.asarray(scores, dtype=float)

        # Trim extreme scores
        if self.trim_percentile is not None:
            lower = np.percentile(scores, self.trim_percentile * 100)
            upper = np.percentile(scores, (1 - self.trim_percentile) * 100)
            scores = np.clip(scores, lower, upper)

        # Compute weights based on target
        if target == "ate":
            weights = treatment / scores + (1 - treatment) / (1 - scores)
        elif target == "att":
            weights = treatment + (1 - treatment) * scores / (1 - scores)
        elif target == "atu":
            weights = treatment * (1 - scores) / scores + (1 - treatment)
        else:
            raise ValueError(f"Unknown target: {target}")

        # Stabilize weights
        if self.stabilized:
            p_treat = np.mean(treatment)
            if target == "ate":
                weights = treatment * p_treat / scores + (1 - treatment) * (1 - p_treat) / (1 - scores)
            elif target == "att":
                weights = treatment + (1 - treatment) * p_treat * scores / ((1 - p_treat) * (1 - scores))
            elif target == "atu":
                weights = treatment * (1 - p_treat) * (1 - scores) / (p_treat * scores) + (1 - treatment)

        # Cap weights
        if self.weight_cap is not None:
            weights = np.clip(weights, 0, self.weight_cap)

        return cast(np.ndarray, weights)

    def estimate_effect(
        self,
        outcome: np.ndarray,
        treatment: np.ndarray,
        scores: np.ndarray,
        target: str = "ate",
        alpha: float = 0.05,
    ) -> TreatmentEffectResult:
        """
        Estimate treatment effect using IPW.

        Args:
            outcome: Outcome variable
            treatment: Binary treatment indicator
            scores: Propensity scores
            target: Target estimand ('ate', 'att', 'atu')
            alpha: Significance level for CI

        Returns:
            TreatmentEffectResult with effect estimate and CI
        """
        outcome = np.asarray(outcome, dtype=float)
        treatment = np.asarray(treatment, dtype=float)
        scores = np.asarray(scores, dtype=float)

        weights = self.compute_weights(treatment, scores, target)

        # Weighted means
        treated_mask = treatment == 1
        control_mask = treatment == 0

        if target == "ate":
            # ATE: E[Y(1)] - E[Y(0)]
            weighted_y1 = np.sum(weights[treated_mask] * outcome[treated_mask]) / np.sum(weights[treated_mask])
            weighted_y0 = np.sum(weights[control_mask] * outcome[control_mask]) / np.sum(weights[control_mask])
        elif target == "att":
            # ATT: E[Y(1) - Y(0) | T=1]
            weighted_y1 = np.mean(outcome[treated_mask])
            weighted_y0 = np.sum(weights[control_mask] * outcome[control_mask]) / np.sum(weights[control_mask])
        else:  # atu
            # ATU: E[Y(1) - Y(0) | T=0]
            weighted_y1 = np.sum(weights[treated_mask] * outcome[treated_mask]) / np.sum(weights[treated_mask])
            weighted_y0 = np.mean(outcome[control_mask])

        effect = weighted_y1 - weighted_y0

        # Bootstrap standard error
        n_bootstrap = 1000
        boot_effects = []
        n = len(outcome)

        for _ in range(n_bootstrap):
            idx = np.random.choice(n, n, replace=True)
            boot_outcome = outcome[idx]
            boot_treatment = treatment[idx]
            boot_scores = scores[idx]

            boot_weights = self.compute_weights(boot_treatment, boot_scores, target)

            t_mask = boot_treatment == 1
            c_mask = boot_treatment == 0

            if np.sum(t_mask) == 0 or np.sum(c_mask) == 0:
                continue

            if target == "ate":
                y1 = np.sum(boot_weights[t_mask] * boot_outcome[t_mask]) / np.sum(boot_weights[t_mask])
                y0 = np.sum(boot_weights[c_mask] * boot_outcome[c_mask]) / np.sum(boot_weights[c_mask])
            elif target == "att":
                y1 = np.mean(boot_outcome[t_mask])
                y0 = np.sum(boot_weights[c_mask] * boot_outcome[c_mask]) / np.sum(boot_weights[c_mask])
            else:
                y1 = np.sum(boot_weights[t_mask] * boot_outcome[t_mask]) / np.sum(boot_weights[t_mask])
                y0 = np.mean(boot_outcome[c_mask])

            boot_effects.append(y1 - y0)

        std_error = np.std(boot_effects) if boot_effects else 0

        # Confidence interval
        z = stats.norm.ppf(1 - alpha / 2)
        ci_lower = effect - z * std_error
        ci_upper = effect + z * std_error

        # P-value (two-tailed)
        if std_error > 0:
            z_stat = effect / std_error
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        else:
            p_value = 1.0

        return TreatmentEffectResult(
            effect_type=target.upper(),
            estimate=effect,
            std_error=std_error,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            method=f"IPW ({self.method})",
            n_treated=int(np.sum(treatment)),
            n_control=int(np.sum(1 - treatment)),
        )


class BalanceAssessor:
    """
    Assess covariate balance between treatment groups.

    Metrics:
    - Standardized Mean Difference (SMD)
    - Variance Ratio
    - Kolmogorov-Smirnov statistic
    - Overlap statistics

    Example:
        >>> assessor = BalanceAssessor(smd_threshold=0.1)
        >>> result = assessor.assess(X, treatment, weights=ipw_weights)
    """

    def __init__(
        self,
        smd_threshold: float = 0.1,
        vr_threshold: Tuple[float, float] = (0.5, 2.0),
    ):
        """
        Initialize balance assessor.

        Args:
            smd_threshold: Threshold for acceptable SMD (typically 0.1 or 0.25)
            vr_threshold: Acceptable range for variance ratio
        """
        self.smd_threshold = smd_threshold
        self.vr_threshold = vr_threshold

    def assess(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        treatment: np.ndarray,
        weights: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> BalanceDiagnostics:
        """
        Assess covariate balance.

        Args:
            X: Covariate matrix
            treatment: Binary treatment indicator
            weights: Optional weights (from matching or IPW)
            feature_names: Names of features

        Returns:
            BalanceDiagnostics with balance metrics
        """
        if isinstance(X, pd.DataFrame):
            feature_names = list(X.columns)
            X = X.values.astype(float)
        else:
            X = np.asarray(X, dtype=float)
            feature_names = feature_names or [f"X{i}" for i in range(X.shape[1])]

        treatment = np.asarray(treatment, dtype=float).ravel()

        if weights is None:
            weights = np.ones(len(treatment))
        else:
            weights = np.asarray(weights, dtype=float)

        treated_mask = treatment == 1
        control_mask = treatment == 0

        smd_dict = {}
        vr_dict = {}
        ks_dict = {}

        for i, name in enumerate(feature_names):
            x = X[:, i]

            # Weighted statistics
            smd = self._compute_smd(x, treated_mask, control_mask, weights)
            vr = self._compute_variance_ratio(x, treated_mask, control_mask, weights)
            ks_stat, ks_pval = self._compute_ks(x, treated_mask, control_mask, weights)

            smd_dict[name] = float(smd)
            vr_dict[name] = float(vr)
            ks_dict[name] = {
                "statistic": float(ks_stat),
                "p_value": float(ks_pval),
            }

        # Overall balance summary
        mean_smd = np.mean(np.abs(list(smd_dict.values())))
        max_smd = np.max(np.abs(list(smd_dict.values())))
        n_unbalanced = sum(1 for v in smd_dict.values() if abs(v) > self.smd_threshold)

        overall = {
            "mean_absolute_smd": float(mean_smd),
            "max_absolute_smd": float(max_smd),
            "n_covariates": len(feature_names),
            "n_unbalanced": n_unbalanced,
            "proportion_balanced": float(1 - n_unbalanced / len(feature_names)),
        }

        balance_achieved = max_smd <= self.smd_threshold

        return BalanceDiagnostics(
            standardized_differences=smd_dict,
            variance_ratios=vr_dict,
            ks_statistics=ks_dict,
            overall_balance=overall,
            balance_achieved=balance_achieved,
        )

    def _compute_smd(
        self,
        x: np.ndarray,
        treated_mask: np.ndarray,
        control_mask: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        """Compute standardized mean difference."""
        # Weighted means
        w_t = weights[treated_mask]
        w_c = weights[control_mask]
        x_t = x[treated_mask]
        x_c = x[control_mask]

        # Handle empty groups
        if len(x_t) == 0 or len(x_c) == 0:
            return float("nan")
        if np.sum(w_t) == 0 or np.sum(w_c) == 0:
            return float("nan")

        mean_t = np.average(x_t, weights=w_t)
        mean_c = np.average(x_c, weights=w_c)

        # Pooled standard deviation (unweighted, from original sample)
        var_t = np.var(x_t) if len(x_t) > 1 else 0
        var_c = np.var(x_c) if len(x_c) > 1 else 0
        pooled_std = np.sqrt((var_t + var_c) / 2)

        if pooled_std == 0:
            return 0.0

        return float((mean_t - mean_c) / pooled_std)

    def _compute_variance_ratio(
        self,
        x: np.ndarray,
        treated_mask: np.ndarray,
        control_mask: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        """Compute variance ratio."""
        x_t = x[treated_mask]
        x_c = x[control_mask]
        w_t = weights[treated_mask]
        w_c = weights[control_mask]

        # Handle empty groups
        if len(x_t) == 0 or len(x_c) == 0:
            return float("nan")
        if np.sum(w_t) == 0 or np.sum(w_c) == 0:
            return float("nan")

        # Weighted variance
        mean_t = np.average(x_t, weights=w_t)
        mean_c = np.average(x_c, weights=w_c)

        var_t = np.average((x_t - mean_t) ** 2, weights=w_t)
        var_c = np.average((x_c - mean_c) ** 2, weights=w_c)

        if var_c == 0:
            return float("inf") if var_t > 0 else 1.0

        return float(var_t / var_c)

    def _compute_ks(
        self,
        x: np.ndarray,
        treated_mask: np.ndarray,
        control_mask: np.ndarray,
        weights: np.ndarray,
    ) -> Tuple[float, float]:
        """Compute Kolmogorov-Smirnov statistic."""
        x_t = x[treated_mask]
        x_c = x[control_mask]

        # Unweighted KS test for simplicity
        try:
            stat, pval = stats.ks_2samp(x_t, x_c)
            return stat, pval
        except Exception:
            return 0.0, 1.0


# =============================================================================
# Convenience Functions
# =============================================================================


def estimate_propensity_scores(
    df: pd.DataFrame,
    treatment_col: str,
    covariates: List[str],
    regularization: float = 0.0,
    include_scores: bool = False,
) -> Dict[str, Any]:
    """
    Estimate propensity scores using logistic regression.

    Args:
        df: DataFrame with treatment and covariates
        treatment_col: Name of binary treatment column
        covariates: List of covariate column names
        regularization: L2 regularization strength
        include_scores: If True, include full scores array (for internal use)

    Returns:
        Dictionary with coefficients, diagnostics, and optionally scores
    """
    X = df[covariates].copy()
    treatment = df[treatment_col].values

    estimator = PropensityScoreEstimator(regularization=regularization)
    result = estimator.fit(X, treatment)

    # Build response with meaningful statistics (not raw scores)
    response = {
        "status": "success",
        "analysis_type": "propensity_score_estimation",
        "treatment_column": treatment_col,
        "covariates": covariates,
        **result.to_dict(),
        # Add score summary statistics instead of full array
        "score_summary": {
            "min": float(np.nanmin(result.scores)),
            "max": float(np.nanmax(result.scores)),
            "mean": float(np.nanmean(result.scores)),
            "std": float(np.nanstd(result.scores)),
            "median": float(np.nanmedian(result.scores)),
            "q25": float(np.nanpercentile(result.scores, 25)),
            "q75": float(np.nanpercentile(result.scores, 75)),
        },
    }

    # Only include full scores if explicitly requested (for internal pipeline use)
    if include_scores:
        response["_scores"] = result.scores.tolist()

    return response


def match_propensity_scores(
    df: pd.DataFrame,
    treatment_col: str,
    score_col: Optional[str] = None,
    covariates: Optional[List[str]] = None,
    method: str = "nearest",
    caliper: Optional[float] = 0.2,
    caliper_scale: str = "std",
    replacement: bool = False,
) -> Dict[str, Any]:
    """
    Perform propensity score matching.

    Args:
        df: DataFrame with treatment and either scores or covariates
        treatment_col: Name of binary treatment column
        score_col: Name of propensity score column (if pre-computed)
        covariates: Covariates to use for PS estimation (if score_col not provided)
        method: Matching method ('nearest' or 'optimal')
        caliper: Maximum distance for matching
        caliper_scale: 'std' or 'absolute'
        replacement: Allow matching with replacement
        include_indices: If True, include full matched indices (for internal use)

    Returns:
        Dictionary with matching results and summary statistics
    """
    treatment = df[treatment_col].values

    # Get or estimate propensity scores
    if score_col is not None:
        scores = df[score_col].values
        ps_result = None
    elif covariates is not None:
        estimator = PropensityScoreEstimator()
        ps_result = estimator.fit(df[covariates], treatment)
        scores = ps_result.scores
    else:
        raise ValueError("Must provide either score_col or covariates")

    # Perform matching
    matcher = PropensityScoreMatcher(
        method=method,
        caliper=caliper,
        caliper_scale=caliper_scale,
        replacement=replacement,
    )
    match_result = matcher.match(scores, treatment)

    result = {
        "status": "success",
        "analysis_type": "propensity_score_matching",
        "treatment_column": treatment_col,
        "method": method,
        **match_result.to_dict(),
        # Include summary of matched indices instead of full arrays
        "matching_summary": {
            "total_treated": int(np.sum(treatment)),
            "total_control": int(np.sum(1 - treatment)),
            "matched_pairs": match_result.n_matched,
            "unmatched_treated": match_result.n_unmatched_treated,
            "unmatched_control": match_result.n_unmatched_control,
        },
    }

    if ps_result is not None:
        result["propensity_model"] = ps_result.to_dict()

    return result


def estimate_treatment_effect(
    df: pd.DataFrame,
    outcome_col: str,
    treatment_col: str,
    score_col: Optional[str] = None,
    covariates: Optional[List[str]] = None,
    method: str = "ipw",
    target: str = "ate",
    stabilized: bool = True,
) -> Dict[str, Any]:
    """
    Estimate treatment effect using inverse probability weighting.

    Args:
        df: DataFrame with outcome, treatment, and scores/covariates
        outcome_col: Name of outcome column
        treatment_col: Name of binary treatment column
        score_col: Name of propensity score column (if pre-computed)
        covariates: Covariates for PS estimation (if score_col not provided)
        method: Weighting method ('ipw' or 'iptw')
        target: Target estimand ('ate', 'att', 'atu')
        stabilized: Use stabilized weights

    Returns:
        Dictionary with treatment effect estimate and CI
    """
    outcome = df[outcome_col].values
    treatment = df[treatment_col].values

    # Get or estimate propensity scores
    if score_col is not None:
        scores = df[score_col].values
        ps_result = None
    elif covariates is not None:
        estimator = PropensityScoreEstimator()
        ps_result = estimator.fit(df[covariates], treatment)
        scores = ps_result.scores
    else:
        raise ValueError("Must provide either score_col or covariates")

    # Estimate treatment effect
    ipw = IPWeighting(method=method, stabilized=stabilized)
    effect_result = ipw.estimate_effect(outcome, treatment, scores, target)

    result = {
        "status": "success",
        "analysis_type": "treatment_effect_estimation",
        "outcome_column": outcome_col,
        "treatment_column": treatment_col,
        "method": method,
        "target": target,
        **effect_result.to_dict(),
    }

    if ps_result is not None:
        result["propensity_model"] = {
            "c_statistic": ps_result.model_metrics["c_statistic"],
            "pseudo_r2": ps_result.model_metrics["pseudo_r2"],
        }

    return result


def assess_balance(
    df: pd.DataFrame,
    treatment_col: str,
    covariates: List[str],
    weights: Optional[np.ndarray] = None,
    smd_threshold: float = 0.1,
) -> Dict[str, Any]:
    """
    Assess covariate balance between treatment groups.

    Args:
        df: DataFrame with treatment and covariates
        treatment_col: Name of binary treatment column
        covariates: List of covariate column names
        weights: Optional weights from matching or IPW
        smd_threshold: Threshold for acceptable SMD

    Returns:
        Dictionary with balance diagnostics
    """
    X = df[covariates].values
    treatment = df[treatment_col].values

    assessor = BalanceAssessor(smd_threshold=smd_threshold)
    result = assessor.assess(X, treatment, weights, covariates)

    return {
        "status": "success",
        "analysis_type": "balance_assessment",
        "treatment_column": treatment_col,
        "covariates": covariates,
        "smd_threshold": smd_threshold,
        **result.to_dict(),
    }


def propensity_score_analysis(
    df: pd.DataFrame,
    outcome_col: str,
    treatment_col: str,
    covariates: List[str],
    method: str = "matching",  # 'matching' or 'ipw'
    target: str = "ate",
    caliper: Optional[float] = 0.2,
) -> Dict[str, Any]:
    """
    Complete propensity score analysis workflow.

    Performs:
    1. Propensity score estimation
    2. Balance assessment (before)
    3. Matching or IPW
    4. Balance assessment (after)
    5. Treatment effect estimation

    Args:
        df: DataFrame with outcome, treatment, and covariates
        outcome_col: Name of outcome column
        treatment_col: Name of binary treatment column
        covariates: List of covariate column names
        method: 'matching' or 'ipw'
        target: Target estimand ('ate', 'att', 'atu')
        caliper: Caliper for matching (in std deviations)

    Returns:
        Dictionary with complete analysis results
    """
    treatment = df[treatment_col].values
    outcome = df[outcome_col].values
    X = df[covariates]

    # Step 1: Estimate propensity scores
    estimator = PropensityScoreEstimator()
    ps_result = estimator.fit(X, treatment)
    scores = ps_result.scores

    # Step 2: Balance before
    assessor = BalanceAssessor()
    balance_before = assessor.assess(X, treatment, feature_names=covariates)

    # Step 3 & 4: Apply method and assess balance after
    if method == "matching":
        matcher = PropensityScoreMatcher(caliper=caliper)
        match_result = matcher.match(scores, treatment)

        # Create matched sample
        matched_idx = np.concatenate([match_result.matched_treated_idx, match_result.matched_control_idx]).astype(int)
        X_matched = X.iloc[matched_idx]
        treatment_matched = treatment[matched_idx]
        outcome_matched = outcome[matched_idx]

        balance_after = assessor.assess(X_matched, treatment_matched, feature_names=covariates)

        # Treatment effect on matched sample
        treated_outcomes = outcome_matched[treatment_matched == 1]
        control_outcomes = outcome_matched[treatment_matched == 0]

        effect = np.mean(treated_outcomes) - np.mean(control_outcomes)
        se = np.sqrt(
            np.var(treated_outcomes) / len(treated_outcomes) + np.var(control_outcomes) / len(control_outcomes)
        )

        method_details = {
            "n_matched_pairs": match_result.n_matched,
            "matching_rate": match_result.n_matched / np.sum(treatment),
            "caliper_used": match_result.caliper_used,
        }

    else:  # IPW
        ipw = IPWeighting(stabilized=True)
        weights = ipw.compute_weights(treatment, scores, target)

        balance_after = assessor.assess(X, treatment, weights, covariates)

        effect_result = ipw.estimate_effect(outcome, treatment, scores, target)
        effect = effect_result.estimate
        se = effect_result.std_error

        method_details = {
            "weight_mean": float(np.mean(weights)),
            "weight_std": float(np.std(weights)),
            "weight_max": float(np.max(weights)),
        }

    # Confidence interval
    ci_lower = effect - 1.96 * se
    ci_upper = effect + 1.96 * se
    p_value = 2 * (1 - stats.norm.cdf(abs(effect / se))) if se > 0 else 1.0

    return {
        "status": "success",
        "analysis_type": "propensity_score_analysis",
        "outcome_column": outcome_col,
        "treatment_column": treatment_col,
        "covariates": covariates,
        "method": method,
        "target": target,
        "sample_sizes": {
            "n_treated": int(np.sum(treatment)),
            "n_control": int(np.sum(1 - treatment)),
            "n_total": len(treatment),
        },
        "propensity_model": ps_result.to_dict(),
        "balance_before": balance_before.to_dict(),
        "balance_after": balance_after.to_dict(),
        "method_details": method_details,
        "treatment_effect": {
            "estimate": float(effect),
            "std_error": float(se),
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
        },
    }

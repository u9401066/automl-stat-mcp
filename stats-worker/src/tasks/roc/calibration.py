"""
Calibration Analysis Module

Analyze calibration of predicted probabilities.

Contains:
    - CalibrationAnalyzer: Hosmer-Lemeshow test, Brier score, calibration curve
"""

from typing import Dict, List, Tuple

import numpy as np
from scipy import stats

from .types import CalibrationResult


class CalibrationAnalyzer:
    """
    Analyze calibration of predicted probabilities.

    Includes:
    - Hosmer-Lemeshow test
    - Calibration slope and intercept
    - Brier score
    - Calibration curve (reliability diagram)

    Example:
        >>> analyzer = CalibrationAnalyzer(n_bins=10)
        >>> result = analyzer.analyze(y_true, y_prob)
        >>> print(f"Hosmer-Lemeshow p-value: {result.hosmer_lemeshow_pvalue:.4f}")
    """

    def __init__(self, n_bins: int = 10):
        """
        Initialize analyzer.

        Args:
            n_bins: Number of bins for calibration analysis
        """
        self.n_bins = n_bins

    def analyze(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
    ) -> CalibrationResult:
        """
        Perform calibration analysis.

        Args:
            y_true: True binary labels (0/1)
            y_prob: Predicted probabilities

        Returns:
            CalibrationResult with all metrics
        """
        y_true = np.asarray(y_true).ravel()
        y_prob = np.asarray(y_prob).ravel()

        # Brier score
        brier = np.mean((y_prob - y_true) ** 2)

        # Calibration in the large (mean predicted vs observed)
        citl = np.mean(y_prob) - np.mean(y_true)

        # Bin data for Hosmer-Lemeshow and calibration curve
        bins = self._create_bins(y_true, y_prob)

        # Hosmer-Lemeshow test
        hl_stat, hl_pvalue = self._hosmer_lemeshow(bins)

        # Calibration slope and intercept
        slope, intercept = self._calibration_regression(y_true, y_prob)

        # Well calibrated if HL p > 0.05 and slope close to 1
        well_calibrated = hl_pvalue > 0.05 and 0.8 < slope < 1.2

        return CalibrationResult(
            hosmer_lemeshow_statistic=hl_stat,
            hosmer_lemeshow_pvalue=hl_pvalue,
            brier_score=brier,
            calibration_slope=slope,
            calibration_intercept=intercept,
            calibration_in_the_large=citl,
            bins=bins,
            well_calibrated=well_calibrated,
        )

    def _create_bins(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
    ) -> List[Dict[str, float]]:
        """Create calibration bins."""
        try:
            bin_edges = np.percentile(y_prob, np.linspace(0, 100, self.n_bins + 1))
            bin_edges = np.unique(bin_edges)
        except Exception:
            bin_edges = np.linspace(0, 1, self.n_bins + 1)

        bins = []
        for i in range(len(bin_edges) - 1):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]

            if i == len(bin_edges) - 2:
                mask = (y_prob >= lower) & (y_prob <= upper)
            else:
                mask = (y_prob >= lower) & (y_prob < upper)

            n_in_bin = np.sum(mask)
            if n_in_bin > 0:
                mean_pred = np.mean(y_prob[mask])
                mean_obs = np.mean(y_true[mask])
                n_events = np.sum(y_true[mask])
            else:
                mean_pred = (lower + upper) / 2
                mean_obs = 0
                n_events = 0

            bins.append(
                {
                    "bin_lower": float(lower),
                    "bin_upper": float(upper),
                    "n_samples": int(n_in_bin),
                    "n_events": int(n_events),
                    "mean_predicted": float(mean_pred),
                    "mean_observed": float(mean_obs),
                }
            )

        return bins

    def _hosmer_lemeshow(
        self,
        bins: List[Dict[str, float]],
    ) -> Tuple[float, float]:
        """Compute Hosmer-Lemeshow statistic."""
        hl_stat = 0.0
        n_bins_used = 0

        for b in bins:
            n = b["n_samples"]
            if n == 0:
                continue

            n_bins_used += 1
            observed = b["n_events"]
            expected = n * b["mean_predicted"]

            if expected > 0 and expected < n:
                hl_stat += (observed - expected) ** 2 / (expected * (1 - b["mean_predicted"]))

        df = max(1, n_bins_used - 2)
        p_value = 1 - stats.chi2.cdf(hl_stat, df)

        return hl_stat, p_value

    def _calibration_regression(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Compute calibration slope and intercept using logistic regression.

        Ideal: slope = 1, intercept = 0
        """
        y_prob_clipped = np.clip(y_prob, 1e-10, 1 - 1e-10)
        logit_pred = np.log(y_prob_clipped / (1 - y_prob_clipped))

        try:
            w = y_prob_clipped * (1 - y_prob_clipped)
            w = np.maximum(w, 1e-10)

            mean_logit = np.average(logit_pred, weights=w)
            mean_y = np.average(y_true, weights=w)

            num = np.sum(w * (logit_pred - mean_logit) * (y_true - mean_y))
            den = np.sum(w * (logit_pred - mean_logit) ** 2)

            slope = num / den if den > 0 else 1.0
            intercept = mean_y - slope * mean_logit

        except Exception:
            slope = 1.0
            intercept = 0.0

        return slope, intercept

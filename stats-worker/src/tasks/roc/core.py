"""
ROC Core Analysis Module

Core ROC curve analysis and DeLong test.

Contains:
    - ROCAnalyzer: Comprehensive ROC curve analysis
    - DeLongTest: DeLong test for comparing two correlated AUCs
"""
from typing import Dict

import numpy as np
from scipy import stats
from scipy.special import ndtri

from .types import AUCComparisonResult, ROCCurveResult, ROCPoint


class ROCAnalyzer:
    """
    Comprehensive ROC curve analysis.

    Features:
    - ROC curve computation
    - AUC with DeLong confidence intervals
    - Optimal threshold selection
    - Multiple threshold criteria

    Example:
        >>> analyzer = ROCAnalyzer()
        >>> result = analyzer.compute_roc(y_true, y_scores)
        >>> print(f"AUC: {result.auc:.3f} [{result.auc_ci_lower:.3f}, {result.auc_ci_upper:.3f}]")
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize analyzer.

        Args:
            alpha: Significance level for confidence intervals
        """
        self.alpha = alpha

    def compute_roc(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        threshold_method: str = "youden",
        pos_label: int = 1,
    ) -> ROCCurveResult:
        """
        Compute ROC curve with AUC and confidence interval.

        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities or scores
            threshold_method: Method for optimal threshold ('youden', 'closest_to_01', 'sensitivity_specificity')
            pos_label: Label of positive class

        Returns:
            ROCCurveResult with curve points, AUC, and CI
        """
        y_true = np.asarray(y_true).ravel()
        y_scores = np.asarray(y_scores).ravel()

        # Convert to binary
        y_binary = (y_true == pos_label).astype(int)

        n_pos = np.sum(y_binary)
        n_neg = len(y_binary) - n_pos

        if n_pos == 0 or n_neg == 0:
            raise ValueError("Need at least one positive and one negative sample")

        # Sort by scores descending
        sorted_idx = np.argsort(y_scores)[::-1]
        y_sorted = y_binary[sorted_idx]
        scores_sorted = y_scores[sorted_idx]

        # Compute TPR and FPR at each threshold
        tps = np.cumsum(y_sorted)
        fps = np.cumsum(1 - y_sorted)

        tpr = tps / n_pos
        fpr = fps / n_neg

        # Add origin point
        tpr = np.concatenate([[0], tpr])
        fpr = np.concatenate([[0], fpr])
        thresholds = np.concatenate([[scores_sorted[0] + 1], scores_sorted])

        # Compute AUC using trapezoidal rule
        auc = np.trapz(tpr, fpr)

        # DeLong variance for AUC
        auc_se = self._delong_variance(y_binary, y_scores)

        # Confidence interval
        z = ndtri(1 - self.alpha / 2)
        auc_ci_lower = max(0, auc - z * auc_se)
        auc_ci_upper = min(1, auc + z * auc_se)

        # Build curve points
        curve_points = []
        for i in range(len(thresholds)):
            # Compute PPV/NPV at this threshold
            pred_pos = np.sum(y_scores >= thresholds[i])
            pred_neg = len(y_scores) - pred_pos

            tp = tps[i-1] if i > 0 else 0
            fp = fps[i-1] if i > 0 else 0
            n_pos - tp
            tn = n_neg - fp

            ppv = tp / pred_pos if pred_pos > 0 else None
            npv = tn / pred_neg if pred_neg > 0 else None

            point = ROCPoint(
                threshold=thresholds[i],
                fpr=fpr[i],
                tpr=tpr[i],
                specificity=1 - fpr[i],
                sensitivity=tpr[i],
                ppv=ppv,
                npv=npv,
            )
            curve_points.append(point)

        # Find optimal threshold
        optimal_threshold = self._find_optimal_threshold(
            thresholds, tpr, fpr, threshold_method
        )

        return ROCCurveResult(
            auc=float(auc),
            auc_ci_lower=float(auc_ci_lower),
            auc_ci_upper=float(auc_ci_upper),
            auc_se=float(auc_se),
            curve_points=curve_points,
            optimal_threshold=float(optimal_threshold),
            optimal_method=threshold_method,
            n_positive=int(n_pos),
            n_negative=int(n_neg),
        )

    def _delong_variance(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
    ) -> float:
        """
        Compute DeLong variance estimate for AUC.

        Based on: DeLong et al. (1988)
        """
        pos_scores = y_scores[y_true == 1]
        neg_scores = y_scores[y_true == 0]

        n_pos = len(pos_scores)
        n_neg = len(neg_scores)

        if n_pos == 0 or n_neg == 0:
            return 0.0

        # Placement values (V statistics)
        v_pos = np.zeros(n_pos)
        for i, pos_score in enumerate(pos_scores):
            v_pos[i] = np.mean(pos_score > neg_scores) + 0.5 * np.mean(pos_score == neg_scores)

        v_neg = np.zeros(n_neg)
        for i, neg_score in enumerate(neg_scores):
            v_neg[i] = np.mean(neg_score < pos_scores) + 0.5 * np.mean(neg_score == pos_scores)

        # Variance components
        s10 = np.var(v_pos, ddof=1) if n_pos > 1 else 0
        s01 = np.var(v_neg, ddof=1) if n_neg > 1 else 0

        # Total variance
        variance = s10 / n_pos + s01 / n_neg

        return float(np.sqrt(variance))

    def _find_optimal_threshold(
        self,
        thresholds: np.ndarray,
        tpr: np.ndarray,
        fpr: np.ndarray,
        method: str,
    ) -> float:
        """Find optimal threshold using specified method."""
        if method == "youden":
            j_scores = tpr - fpr
            optimal_idx = np.argmax(j_scores)

        elif method == "closest_to_01":
            distances = np.sqrt(fpr ** 2 + (1 - tpr) ** 2)
            optimal_idx = np.argmin(distances)

        elif method == "sensitivity_specificity":
            diff = np.abs(tpr - (1 - fpr))
            optimal_idx = np.argmin(diff)

        else:
            j_scores = tpr - fpr
            optimal_idx = np.argmax(j_scores)

        return float(thresholds[optimal_idx])

    def find_threshold_for_sensitivity(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        target_sensitivity: float,
        pos_label: int = 1,
    ) -> Dict[str, float]:
        """
        Find threshold that achieves target sensitivity.

        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities
            target_sensitivity: Desired sensitivity (e.g., 0.90)
            pos_label: Label of positive class

        Returns:
            Dictionary with threshold, achieved sensitivity, and specificity
        """
        result = self.compute_roc(y_true, y_scores, pos_label=pos_label)

        for point in result.curve_points:
            if point.sensitivity >= target_sensitivity:
                return {
                    "threshold": point.threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                    "target_achieved": True,
                }

        best_point = max(result.curve_points, key=lambda p: p.sensitivity)
        return {
            "threshold": best_point.threshold,
            "sensitivity": best_point.sensitivity,
            "specificity": best_point.specificity,
            "target_achieved": False,
        }

    def find_threshold_for_specificity(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        target_specificity: float,
        pos_label: int = 1,
    ) -> Dict[str, float]:
        """
        Find threshold that achieves target specificity.

        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities
            target_specificity: Desired specificity (e.g., 0.95)
            pos_label: Label of positive class

        Returns:
            Dictionary with threshold, achieved specificity, and sensitivity
        """
        result = self.compute_roc(y_true, y_scores, pos_label=pos_label)

        for point in reversed(result.curve_points):
            if point.specificity >= target_specificity:
                return {
                    "threshold": point.threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                    "target_achieved": True,
                }

        best_point = max(result.curve_points, key=lambda p: p.specificity)
        return {
            "threshold": best_point.threshold,
            "sensitivity": best_point.sensitivity,
            "specificity": best_point.specificity,
            "target_achieved": False,
        }


class DeLongTest:
    """
    DeLong test for comparing two correlated AUCs.

    Tests whether two ROC curves from the same sample have
    significantly different AUCs.

    Example:
        >>> test = DeLongTest()
        >>> result = test.compare(y_true, scores1, scores2)
        >>> print(f"p-value: {result.p_value:.4f}")
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize test.

        Args:
            alpha: Significance level
        """
        self.alpha = alpha

    def compare(
        self,
        y_true: np.ndarray,
        scores1: np.ndarray,
        scores2: np.ndarray,
        pos_label: int = 1,
    ) -> AUCComparisonResult:
        """
        Compare two AUCs using DeLong test.

        Args:
            y_true: True binary labels
            scores1: Predicted probabilities from model 1
            scores2: Predicted probabilities from model 2
            pos_label: Label of positive class

        Returns:
            AUCComparisonResult with test statistics
        """
        y_true = np.asarray(y_true).ravel()
        scores1 = np.asarray(scores1).ravel()
        scores2 = np.asarray(scores2).ravel()

        y_binary = (y_true == pos_label).astype(int)

        pos_mask = y_binary == 1
        neg_mask = y_binary == 0

        pos_scores1 = scores1[pos_mask]
        neg_scores1 = scores1[neg_mask]
        pos_scores2 = scores2[pos_mask]
        neg_scores2 = scores2[neg_mask]

        n_pos = len(pos_scores1)
        n_neg = len(neg_scores1)

        # Compute AUCs
        auc1 = self._compute_auc(pos_scores1, neg_scores1)
        auc2 = self._compute_auc(pos_scores2, neg_scores2)

        # Compute placement values
        v10_1 = self._placement_values_pos(pos_scores1, neg_scores1)
        v01_1 = self._placement_values_neg(pos_scores1, neg_scores1)
        v10_2 = self._placement_values_pos(pos_scores2, neg_scores2)
        v01_2 = self._placement_values_neg(pos_scores2, neg_scores2)

        # Covariance matrix components
        s10_11 = np.cov(v10_1, v10_1, ddof=1)[0, 1] if n_pos > 1 else 0
        s10_22 = np.cov(v10_2, v10_2, ddof=1)[0, 1] if n_pos > 1 else 0
        s10_12 = np.cov(v10_1, v10_2, ddof=1)[0, 1] if n_pos > 1 else 0

        s01_11 = np.cov(v01_1, v01_1, ddof=1)[0, 1] if n_neg > 1 else 0
        s01_22 = np.cov(v01_2, v01_2, ddof=1)[0, 1] if n_neg > 1 else 0
        s01_12 = np.cov(v01_1, v01_2, ddof=1)[0, 1] if n_neg > 1 else 0

        var1 = s10_11 / n_pos + s01_11 / n_neg
        var2 = s10_22 / n_pos + s01_22 / n_neg
        cov12 = s10_12 / n_pos + s01_12 / n_neg

        var_diff = var1 + var2 - 2 * cov12
        se_diff = np.sqrt(max(var_diff, 1e-10))

        diff = auc1 - auc2
        z_stat = diff / se_diff

        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

        z_crit = ndtri(1 - self.alpha / 2)
        ci_lower = diff - z_crit * se_diff
        ci_upper = diff + z_crit * se_diff

        return AUCComparisonResult(
            auc1=auc1,
            auc2=auc2,
            difference=diff,
            se_difference=se_diff,
            z_statistic=z_stat,
            p_value=p_value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            significant=p_value < self.alpha,
        )

    def _compute_auc(
        self,
        pos_scores: np.ndarray,
        neg_scores: np.ndarray,
    ) -> float:
        """Compute AUC using Mann-Whitney U statistic."""
        n_pos = len(pos_scores)
        n_neg = len(neg_scores)

        if n_pos == 0 or n_neg == 0:
            return 0.5

        auc = 0
        for pos_score in pos_scores:
            auc += np.sum(pos_score > neg_scores) + 0.5 * np.sum(pos_score == neg_scores)

        return auc / (n_pos * n_neg)

    def _placement_values_pos(
        self,
        pos_scores: np.ndarray,
        neg_scores: np.ndarray,
    ) -> np.ndarray:
        """Compute placement values for positive samples."""
        v = np.zeros(len(pos_scores))
        for i, pos_score in enumerate(pos_scores):
            v[i] = np.mean(pos_score > neg_scores) + 0.5 * np.mean(pos_score == neg_scores)
        return v

    def _placement_values_neg(
        self,
        pos_scores: np.ndarray,
        neg_scores: np.ndarray,
    ) -> np.ndarray:
        """Compute placement values for negative samples."""
        v = np.zeros(len(neg_scores))
        for i, neg_score in enumerate(neg_scores):
            v[i] = np.mean(neg_score < pos_scores) + 0.5 * np.mean(neg_score == pos_scores)
        return v

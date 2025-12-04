"""
ROC/AUC Analysis Module

Provides comprehensive tools for classifier evaluation:
- ROC curve computation with confidence intervals
- AUC calculation with DeLong confidence intervals
- DeLong test for comparing two AUCs
- Optimal threshold selection (Youden's J, cost-based)
- Precision-Recall curves
- Calibration analysis (Hosmer-Lemeshow, calibration curves)
- Net Benefit / Decision Curve Analysis

Reference:
- DeLong et al. (1988). Comparing the areas under two or more
  correlated receiver operating characteristic curves
- Hanley & McNeil (1982). The meaning and use of the area under
  a receiver operating characteristic (ROC) curve
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import ndtri  # inverse normal CDF
import warnings


@dataclass
class ROCPoint:
    """A single point on the ROC curve."""
    threshold: float
    fpr: float  # False Positive Rate (1 - Specificity)
    tpr: float  # True Positive Rate (Sensitivity)
    specificity: float
    sensitivity: float
    ppv: Optional[float] = None  # Positive Predictive Value
    npv: Optional[float] = None  # Negative Predictive Value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": float(self.threshold),
            "fpr": float(self.fpr),
            "tpr": float(self.tpr),
            "specificity": float(self.specificity),
            "sensitivity": float(self.sensitivity),
            "ppv": float(self.ppv) if self.ppv is not None else None,
            "npv": float(self.npv) if self.npv is not None else None,
        }


@dataclass
class ROCCurveResult:
    """Complete ROC curve analysis result."""
    auc: float
    auc_ci_lower: float
    auc_ci_upper: float
    auc_se: float
    curve_points: List[ROCPoint]
    optimal_threshold: float
    optimal_method: str
    n_positive: int
    n_negative: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auc": float(self.auc),
            "auc_ci": {
                "lower": float(self.auc_ci_lower),
                "upper": float(self.auc_ci_upper),
            },
            "auc_se": float(self.auc_se),
            "optimal_threshold": float(self.optimal_threshold),
            "optimal_method": self.optimal_method,
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
            "n_points": len(self.curve_points),
            "curve": [p.to_dict() for p in self.curve_points],
        }


@dataclass
class AUCComparisonResult:
    """Result of comparing two AUCs using DeLong test."""
    auc1: float
    auc2: float
    difference: float
    se_difference: float
    z_statistic: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auc1": float(self.auc1),
            "auc2": float(self.auc2),
            "difference": float(self.difference),
            "se_difference": float(self.se_difference),
            "z_statistic": float(self.z_statistic),
            "p_value": float(self.p_value),
            "ci_difference": {
                "lower": float(self.ci_lower),
                "upper": float(self.ci_upper),
            },
            "significant": self.significant,
        }


@dataclass
class CalibrationResult:
    """Calibration analysis result."""
    hosmer_lemeshow_statistic: float
    hosmer_lemeshow_pvalue: float
    brier_score: float
    calibration_slope: float
    calibration_intercept: float
    calibration_in_the_large: float
    bins: List[Dict[str, float]]
    well_calibrated: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hosmer_lemeshow": {
                "statistic": float(self.hosmer_lemeshow_statistic),
                "p_value": float(self.hosmer_lemeshow_pvalue),
            },
            "brier_score": float(self.brier_score),
            "calibration_slope": float(self.calibration_slope),
            "calibration_intercept": float(self.calibration_intercept),
            "calibration_in_the_large": float(self.calibration_in_the_large),
            "bins": self.bins,
            "well_calibrated": self.well_calibrated,
        }


@dataclass
class PrecisionRecallResult:
    """Precision-Recall curve result."""
    auc_pr: float
    curve_points: List[Dict[str, float]]
    average_precision: float
    f1_optimal_threshold: float
    f1_max: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auc_pr": float(self.auc_pr),
            "average_precision": float(self.average_precision),
            "f1_optimal_threshold": float(self.f1_optimal_threshold),
            "f1_max": float(self.f1_max),
            "n_points": len(self.curve_points),
            "curve": self.curve_points,
        }


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
            fn = n_pos - tp
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
            auc=auc,
            auc_ci_lower=auc_ci_lower,
            auc_ci_upper=auc_ci_upper,
            auc_se=auc_se,
            curve_points=curve_points,
            optimal_threshold=optimal_threshold,
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
        # For each positive, count proportion of negatives with lower score
        v_pos = np.zeros(n_pos)
        for i, pos_score in enumerate(pos_scores):
            v_pos[i] = np.mean(pos_score > neg_scores) + 0.5 * np.mean(pos_score == neg_scores)
        
        # For each negative, count proportion of positives with higher score
        v_neg = np.zeros(n_neg)
        for i, neg_score in enumerate(neg_scores):
            v_neg[i] = np.mean(neg_score < pos_scores) + 0.5 * np.mean(neg_score == pos_scores)
        
        # Variance components
        s10 = np.var(v_pos, ddof=1) if n_pos > 1 else 0
        s01 = np.var(v_neg, ddof=1) if n_neg > 1 else 0
        
        # Total variance
        variance = s10 / n_pos + s01 / n_neg
        
        return np.sqrt(variance)
    
    def _find_optimal_threshold(
        self,
        thresholds: np.ndarray,
        tpr: np.ndarray,
        fpr: np.ndarray,
        method: str,
    ) -> float:
        """Find optimal threshold using specified method."""
        if method == "youden":
            # Maximize Youden's J = sensitivity + specificity - 1 = TPR - FPR
            j_scores = tpr - fpr
            optimal_idx = np.argmax(j_scores)
            
        elif method == "closest_to_01":
            # Minimize distance to (0, 1) corner
            distances = np.sqrt(fpr ** 2 + (1 - tpr) ** 2)
            optimal_idx = np.argmin(distances)
            
        elif method == "sensitivity_specificity":
            # Balance sensitivity and specificity
            # Find where |sensitivity - specificity| is minimized
            diff = np.abs(tpr - (1 - fpr))
            optimal_idx = np.argmin(diff)
            
        else:
            # Default to Youden
            j_scores = tpr - fpr
            optimal_idx = np.argmax(j_scores)
            
        return thresholds[optimal_idx]
    
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
        
        # Find lowest threshold that achieves target sensitivity
        for point in result.curve_points:
            if point.sensitivity >= target_sensitivity:
                return {
                    "threshold": point.threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                    "target_achieved": True,
                }
        
        # If not achievable, return best
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
        
        # Find highest threshold that achieves target specificity
        for point in reversed(result.curve_points):
            if point.specificity >= target_specificity:
                return {
                    "threshold": point.threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                    "target_achieved": True,
                }
        
        # If not achievable, return best
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
        
        # Convert to binary
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
        
        # Variance of AUC1
        var1 = s10_11 / n_pos + s01_11 / n_neg
        
        # Variance of AUC2
        var2 = s10_22 / n_pos + s01_22 / n_neg
        
        # Covariance of AUC1 and AUC2
        cov12 = s10_12 / n_pos + s01_12 / n_neg
        
        # Variance of difference
        var_diff = var1 + var2 - 2 * cov12
        se_diff = np.sqrt(max(var_diff, 1e-10))
        
        # Z statistic
        diff = auc1 - auc2
        z_stat = diff / se_diff
        
        # Two-sided p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # Confidence interval
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
        # Use deciles or equal-width bins
        try:
            # Try quantile-based bins first
            bin_edges = np.percentile(y_prob, np.linspace(0, 100, self.n_bins + 1))
            bin_edges = np.unique(bin_edges)  # Remove duplicates
        except Exception:
            # Fall back to equal-width
            bin_edges = np.linspace(0, 1, self.n_bins + 1)
        
        bins = []
        for i in range(len(bin_edges) - 1):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            
            if i == len(bin_edges) - 2:
                # Include upper bound for last bin
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
            
            bins.append({
                "bin_lower": float(lower),
                "bin_upper": float(upper),
                "n_samples": int(n_in_bin),
                "n_events": int(n_events),
                "mean_predicted": float(mean_pred),
                "mean_observed": float(mean_obs),
            })
        
        return bins
    
    def _hosmer_lemeshow(
        self,
        bins: List[Dict[str, float]],
    ) -> Tuple[float, float]:
        """Compute Hosmer-Lemeshow statistic."""
        hl_stat = 0
        n_bins_used = 0
        
        for b in bins:
            n = b["n_samples"]
            if n == 0:
                continue
                
            n_bins_used += 1
            observed = b["n_events"]
            expected = n * b["mean_predicted"]
            
            # Avoid division by zero
            if expected > 0 and expected < n:
                hl_stat += (observed - expected) ** 2 / (expected * (1 - b["mean_predicted"]))
        
        # Degrees of freedom = n_bins - 2
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
        # Use log-odds (logit) of predicted probabilities
        y_prob_clipped = np.clip(y_prob, 1e-10, 1 - 1e-10)
        logit_pred = np.log(y_prob_clipped / (1 - y_prob_clipped))
        
        # Simple logistic regression to get slope
        # Using weighted least squares approximation
        try:
            # Compute pseudo-outcome
            w = y_prob_clipped * (1 - y_prob_clipped)
            w = np.maximum(w, 1e-10)
            
            # Weighted regression of y on logit(p)
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


class PrecisionRecallAnalyzer:
    """
    Compute Precision-Recall curves.
    
    Especially useful for imbalanced datasets where ROC
    can be overly optimistic.
    
    Example:
        >>> analyzer = PrecisionRecallAnalyzer()
        >>> result = analyzer.compute(y_true, y_scores)
        >>> print(f"Average Precision: {result.average_precision:.3f}")
    """
    
    def compute(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        pos_label: int = 1,
    ) -> PrecisionRecallResult:
        """
        Compute Precision-Recall curve.
        
        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities
            pos_label: Label of positive class
            
        Returns:
            PrecisionRecallResult with curve and metrics
        """
        y_true = np.asarray(y_true).ravel()
        y_scores = np.asarray(y_scores).ravel()
        
        # Convert to binary
        y_binary = (y_true == pos_label).astype(int)
        n_pos = np.sum(y_binary)
        
        # Sort by scores descending
        sorted_idx = np.argsort(y_scores)[::-1]
        y_sorted = y_binary[sorted_idx]
        scores_sorted = y_scores[sorted_idx]
        
        # Compute precision and recall at each threshold
        tps = np.cumsum(y_sorted)
        fps = np.cumsum(1 - y_sorted)
        
        precision = tps / (tps + fps)
        recall = tps / n_pos
        
        # Add starting point (recall=0, precision=1)
        precision = np.concatenate([[1], precision])
        recall = np.concatenate([[0], recall])
        thresholds = np.concatenate([[scores_sorted[0] + 1], scores_sorted])
        
        # Average Precision (area under PR curve)
        # Use trapezoidal approximation
        ap = np.trapz(precision, recall)
        
        # AUC-PR using step function (more accurate)
        auc_pr = np.sum(np.diff(recall) * precision[:-1])
        
        # Find F1-optimal threshold
        f1_scores = 2 * precision * recall / (precision + recall + 1e-10)
        best_f1_idx = np.argmax(f1_scores)
        f1_max = f1_scores[best_f1_idx]
        f1_threshold = thresholds[best_f1_idx]
        
        # Build curve points
        curve_points = []
        for i in range(len(thresholds)):
            curve_points.append({
                "threshold": float(thresholds[i]),
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1_scores[i]),
            })
        
        return PrecisionRecallResult(
            auc_pr=auc_pr,
            curve_points=curve_points,
            average_precision=ap,
            f1_optimal_threshold=f1_threshold,
            f1_max=f1_max,
        )


class NetBenefitAnalyzer:
    """
    Decision Curve Analysis for clinical utility.
    
    Computes net benefit at various threshold probabilities
    to determine clinical usefulness of a prediction model.
    
    Reference:
    Vickers & Elkin (2006). Decision curve analysis
    """
    
    def compute(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        thresholds: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Compute decision curve.
        
        Args:
            y_true: True binary outcomes
            y_prob: Predicted probabilities
            thresholds: Threshold probabilities to evaluate (default: 0-1 by 0.01)
            
        Returns:
            Dictionary with net benefit curves
        """
        y_true = np.asarray(y_true).ravel()
        y_prob = np.asarray(y_prob).ravel()
        
        if thresholds is None:
            thresholds = np.arange(0.01, 1.0, 0.01)
        
        n = len(y_true)
        prevalence = np.mean(y_true)
        
        results = {
            "thresholds": [],
            "model_net_benefit": [],
            "treat_all_net_benefit": [],
            "treat_none_net_benefit": [],
        }
        
        for pt in thresholds:
            # Model net benefit
            pred_pos = y_prob >= pt
            tp = np.sum(pred_pos & (y_true == 1))
            fp = np.sum(pred_pos & (y_true == 0))
            
            nb_model = (tp / n) - (fp / n) * (pt / (1 - pt))
            
            # Treat all
            nb_all = prevalence - (1 - prevalence) * (pt / (1 - pt))
            
            # Treat none
            nb_none = 0
            
            results["thresholds"].append(float(pt))
            results["model_net_benefit"].append(float(nb_model))
            results["treat_all_net_benefit"].append(float(nb_all))
            results["treat_none_net_benefit"].append(float(nb_none))
        
        return results


# =============================================================================
# Convenience Functions
# =============================================================================

def compute_roc_curve(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    threshold_method: str = "youden",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Compute ROC curve with AUC and confidence interval.
    
    Args:
        y_true: True binary labels (0/1)
        y_scores: Predicted probabilities or scores
        threshold_method: Method for optimal threshold ('youden', 'closest_to_01')
        alpha: Significance level for CI (default 0.05 for 95% CI)
        
    Returns:
        Dictionary with ROC curve data, AUC, CI, optimal threshold
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    analyzer = ROCAnalyzer(alpha=alpha)
    result = analyzer.compute_roc(y_true, y_scores, threshold_method)
    
    return {
        "status": "success",
        "analysis_type": "roc_curve",
        **result.to_dict(),
    }


def compare_roc_curves(
    y_true: Union[np.ndarray, pd.Series, List],
    scores1: Union[np.ndarray, pd.Series, List],
    scores2: Union[np.ndarray, pd.Series, List],
    model1_name: str = "Model 1",
    model2_name: str = "Model 2",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Compare two ROC curves using DeLong test.
    
    Args:
        y_true: True binary labels
        scores1: Predicted probabilities from model 1
        scores2: Predicted probabilities from model 2
        model1_name: Name for model 1
        model2_name: Name for model 2
        alpha: Significance level
        
    Returns:
        Dictionary with comparison results
    """
    y_true = np.asarray(y_true)
    scores1 = np.asarray(scores1)
    scores2 = np.asarray(scores2)
    
    test = DeLongTest(alpha=alpha)
    result = test.compare(y_true, scores1, scores2)
    
    # Also compute individual ROC curves
    analyzer = ROCAnalyzer(alpha=alpha)
    roc1 = analyzer.compute_roc(y_true, scores1)
    roc2 = analyzer.compute_roc(y_true, scores2)
    
    return {
        "status": "success",
        "analysis_type": "roc_comparison",
        "model1": {
            "name": model1_name,
            "auc": float(roc1.auc),
            "auc_ci": {"lower": float(roc1.auc_ci_lower), "upper": float(roc1.auc_ci_upper)},
        },
        "model2": {
            "name": model2_name,
            "auc": float(roc2.auc),
            "auc_ci": {"lower": float(roc2.auc_ci_lower), "upper": float(roc2.auc_ci_upper)},
        },
        "comparison": result.to_dict(),
        "conclusion": f"{model1_name} {'significantly better' if result.significant and result.difference > 0 else 'significantly worse' if result.significant and result.difference < 0 else 'not significantly different'} than {model2_name}",
    }


def analyze_calibration(
    y_true: Union[np.ndarray, pd.Series, List],
    y_prob: Union[np.ndarray, pd.Series, List],
    n_bins: int = 10,
) -> Dict[str, Any]:
    """
    Analyze calibration of predicted probabilities.
    
    Args:
        y_true: True binary labels
        y_prob: Predicted probabilities
        n_bins: Number of bins for calibration
        
    Returns:
        Dictionary with calibration metrics
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    
    analyzer = CalibrationAnalyzer(n_bins=n_bins)
    result = analyzer.analyze(y_true, y_prob)
    
    return {
        "status": "success",
        "analysis_type": "calibration",
        **result.to_dict(),
    }


def compute_precision_recall(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
) -> Dict[str, Any]:
    """
    Compute Precision-Recall curve.
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        
    Returns:
        Dictionary with PR curve and metrics
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    analyzer = PrecisionRecallAnalyzer()
    result = analyzer.compute(y_true, y_scores)
    
    return {
        "status": "success",
        "analysis_type": "precision_recall",
        **result.to_dict(),
    }


def find_optimal_threshold(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    method: str = "youden",
    target_metric: Optional[str] = None,
    target_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Find optimal classification threshold.
    
    Methods:
    - youden: Maximize Youden's J (sensitivity + specificity - 1)
    - closest_to_01: Minimize distance to (0, 1) on ROC
    - target_sensitivity: Achieve specific sensitivity
    - target_specificity: Achieve specific specificity
    - f1: Maximize F1 score
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        method: Optimization method
        target_metric: 'sensitivity' or 'specificity' for target-based
        target_value: Target value (e.g., 0.90)
        
    Returns:
        Dictionary with optimal threshold and metrics at that threshold
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    analyzer = ROCAnalyzer()
    
    if method == "target_sensitivity" or target_metric == "sensitivity":
        if target_value is None:
            target_value = 0.90
        result = analyzer.find_threshold_for_sensitivity(y_true, y_scores, target_value)
        method_desc = f"Target sensitivity = {target_value}"
        
    elif method == "target_specificity" or target_metric == "specificity":
        if target_value is None:
            target_value = 0.90
        result = analyzer.find_threshold_for_specificity(y_true, y_scores, target_value)
        method_desc = f"Target specificity = {target_value}"
        
    elif method == "f1":
        pr_analyzer = PrecisionRecallAnalyzer()
        pr_result = pr_analyzer.compute(y_true, y_scores)
        
        threshold = pr_result.f1_optimal_threshold
        
        # Get sensitivity/specificity at this threshold
        roc_result = analyzer.compute_roc(y_true, y_scores)
        for point in roc_result.curve_points:
            if abs(point.threshold - threshold) < 0.001:
                result = {
                    "threshold": threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                    "f1": pr_result.f1_max,
                }
                break
        else:
            result = {"threshold": threshold, "f1": pr_result.f1_max}
        method_desc = "Maximize F1 score"
        
    else:  # youden or closest_to_01
        roc_result = analyzer.compute_roc(y_true, y_scores, threshold_method=method)
        threshold = roc_result.optimal_threshold
        
        for point in roc_result.curve_points:
            if abs(point.threshold - threshold) < 0.001:
                result = {
                    "threshold": threshold,
                    "sensitivity": point.sensitivity,
                    "specificity": point.specificity,
                }
                break
        else:
            result = {"threshold": threshold}
            
        method_desc = "Youden's J" if method == "youden" else "Closest to (0,1)"
    
    # Compute confusion matrix at optimal threshold
    y_pred = (y_scores >= result["threshold"]).astype(int)
    tp = np.sum((y_pred == 1) & (y_true == 1))
    tn = np.sum((y_pred == 0) & (y_true == 0))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    
    return {
        "status": "success",
        "analysis_type": "optimal_threshold",
        "method": method_desc,
        **result,
        "confusion_matrix": {
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
        },
        "ppv": float(tp / (tp + fp)) if (tp + fp) > 0 else None,
        "npv": float(tn / (tn + fn)) if (tn + fn) > 0 else None,
        "accuracy": float((tp + tn) / (tp + tn + fp + fn)),
    }


def full_classifier_evaluation(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    model_name: str = "Model",
) -> Dict[str, Any]:
    """
    Complete classifier evaluation including ROC, PR, and calibration.
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        model_name: Name of the model
        
    Returns:
        Dictionary with complete evaluation results
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    # ROC analysis
    roc_analyzer = ROCAnalyzer()
    roc_result = roc_analyzer.compute_roc(y_true, y_scores)
    
    # PR analysis
    pr_analyzer = PrecisionRecallAnalyzer()
    pr_result = pr_analyzer.compute(y_true, y_scores)
    
    # Calibration analysis
    cal_analyzer = CalibrationAnalyzer()
    cal_result = cal_analyzer.analyze(y_true, y_scores)
    
    # Decision curve
    nb_analyzer = NetBenefitAnalyzer()
    nb_result = nb_analyzer.compute(y_true, y_scores)
    
    return {
        "status": "success",
        "analysis_type": "full_classifier_evaluation",
        "model_name": model_name,
        "n_samples": len(y_true),
        "n_positive": int(np.sum(y_true)),
        "n_negative": int(np.sum(1 - y_true)),
        "prevalence": float(np.mean(y_true)),
        "discrimination": {
            "auc_roc": float(roc_result.auc),
            "auc_roc_ci": {
                "lower": float(roc_result.auc_ci_lower),
                "upper": float(roc_result.auc_ci_upper),
            },
            "auc_pr": float(pr_result.auc_pr),
            "average_precision": float(pr_result.average_precision),
        },
        "calibration": {
            "brier_score": float(cal_result.brier_score),
            "hosmer_lemeshow_p": float(cal_result.hosmer_lemeshow_pvalue),
            "calibration_slope": float(cal_result.calibration_slope),
            "well_calibrated": cal_result.well_calibrated,
        },
        "optimal_thresholds": {
            "youden": float(roc_result.optimal_threshold),
            "f1_max": float(pr_result.f1_optimal_threshold),
        },
        "interpretation": {
            "auc_roc": _interpret_auc(roc_result.auc),
            "calibration": "Good" if cal_result.well_calibrated else "Needs recalibration",
        },
    }


def _interpret_auc(auc: float) -> str:
    """Interpret AUC value."""
    if auc >= 0.9:
        return "Excellent"
    elif auc >= 0.8:
        return "Good"
    elif auc >= 0.7:
        return "Fair"
    elif auc >= 0.6:
        return "Poor"
    else:
        return "Fail (no better than chance)"

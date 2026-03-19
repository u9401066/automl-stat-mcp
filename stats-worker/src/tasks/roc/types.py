"""
ROC Analysis Types Module

Data classes for ROC/AUC analysis results.

Contains:
    - ROCPoint: Single point on the ROC curve
    - ROCCurveResult: Complete ROC curve analysis result
    - AUCComparisonResult: Result of comparing two AUCs
    - CalibrationResult: Calibration analysis result
    - PrecisionRecallResult: Precision-Recall curve result
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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

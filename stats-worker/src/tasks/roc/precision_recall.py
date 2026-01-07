"""
Precision-Recall and Net Benefit Analysis Module

Contains:
    - PrecisionRecallAnalyzer: PR curves for imbalanced data
    - NetBenefitAnalyzer: Decision Curve Analysis
"""
from typing import Any, Dict, Optional

import numpy as np

from .types import PrecisionRecallResult


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
            auc_pr=float(auc_pr),
            curve_points=curve_points,
            average_precision=float(ap),
            f1_optimal_threshold=float(f1_threshold),
            f1_max=float(f1_max),
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

        results: Dict[str, list[float]] = {
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

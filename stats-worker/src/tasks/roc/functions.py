"""
ROC Analysis Convenience Functions

High-level functions for common ROC analysis tasks.

Contains:
    - compute_roc_curve: Single ROC curve with AUC and CI
    - compare_roc_curves: Compare two models with DeLong test
    - analyze_calibration: Calibration analysis
    - compute_precision_recall: PR curve analysis
    - find_optimal_threshold: Find best threshold
    - full_classifier_evaluation: Complete evaluation
    - compare_multiple_models: Multi-model comparison
    - threshold_analysis: Comprehensive threshold analysis
    - generate_publication_report: Publication-ready report
"""
import logging
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from .types import ROCCurveResult
from .core import ROCAnalyzer, DeLongTest
from .calibration import CalibrationAnalyzer
from .precision_recall import PrecisionRecallAnalyzer, NetBenefitAnalyzer

logger = logging.getLogger(__name__)

# Optional visualization support
try:
    from visualization.roc import (
        plot_roc_curve,
        plot_pr_curve,
        plot_calibration_curve,
        plot_confusion_matrix,
        plot_threshold_analysis,
        create_roc_visualizations,
    )
    from visualization.storage import save_figure_to_minio
    from visualization.schemas import VisualizationResult, VisualizationType
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False
    logger.debug("Visualization module not available")


def compute_roc_curve(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    threshold_method: str = "youden",
    alpha: float = 0.05,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    model_name: str = "Model",
) -> Dict[str, Any]:
    """
    Compute ROC curve with AUC and confidence interval.
    
    Args:
        y_true: True binary labels (0/1)
        y_scores: Predicted probabilities or scores
        threshold_method: Method for optimal threshold ('youden', 'closest_to_01')
        alpha: Significance level for CI (default 0.05 for 95% CI)
        generate_visualizations: If True, generate ROC curve plot
        user_id: User ID for MinIO path
        job_id: Job ID for MinIO path
        model_name: Name for the model in plot
        
    Returns:
        Dictionary with ROC curve data, AUC, CI, optimal threshold
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    analyzer = ROCAnalyzer(alpha=alpha)
    result = analyzer.compute_roc(y_true, y_scores, threshold_method)
    
    output = {
        "status": "success",
        "analysis_type": "roc_curve",
        **result.to_dict(),
    }
    
    # Generate visualizations if requested
    if generate_visualizations and HAS_VISUALIZATION and user_id and job_id:
        try:
            # Create ROC curve plot
            fig = plot_roc_curve(
                result.to_dict(),
                title=f"ROC Curve - {model_name}",
                show_optimal_point=True,
            )
            
            # Save to MinIO
            url = save_figure_to_minio(
                fig,
                filename="roc_curve.png",
                user_id=user_id,
                job_id=job_id,
            )
            
            output["visualizations"] = [{
                "type": "roc_curve",
                "url": url,
                "title": f"ROC Curve - {model_name} (AUC={result.auc:.3f})",
            }]
            
            import matplotlib.pyplot as plt
            plt.close(fig)
            
        except Exception as e:
            logger.warning(f"Failed to generate ROC curve visualization: {e}")
    
    return output


def compare_roc_curves(
    y_true: Union[np.ndarray, pd.Series, List],
    scores1: Union[np.ndarray, pd.Series, List],
    scores2: Union[np.ndarray, pd.Series, List],
    model1_name: str = "Model 1",
    model2_name: str = "Model 2",
    alpha: float = 0.05,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
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
        generate_visualizations: If True, generate comparison plot
        user_id: User ID for MinIO path
        job_id: Job ID for MinIO path
        
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
    
    output = {
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
    
    # Generate visualizations if requested
    if generate_visualizations and HAS_VISUALIZATION and user_id and job_id:
        try:
            from visualization.roc import plot_roc_curves_comparison
            
            # Convert ROC results to dict format for plotting
            roc1_dict = roc1.to_dict()
            roc2_dict = roc2.to_dict()
            
            # Create comparison plot
            fig = plot_roc_curves_comparison(
                [roc1_dict, roc2_dict],
                labels=[model1_name, model2_name],
                comparison_result={
                    "difference": float(result.difference),
                    "p_value": float(result.p_value),
                }
            )
            
            # Save to MinIO
            url = save_figure_to_minio(
                fig,
                filename="roc_comparison.png",
                user_id=user_id,
                job_id=job_id,
            )
            
            output["visualizations"] = [{
                "type": "roc_comparison",
                "url": url,
                "title": f"ROC Curve Comparison: {model1_name} vs {model2_name}",
            }]
            
            import matplotlib.pyplot as plt
            plt.close(fig)
            
        except Exception as e:
            logger.warning(f"Failed to generate ROC comparison visualization: {e}")
    
    return output


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
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete classifier evaluation including ROC, PR, and calibration.
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        model_name: Name of the model
        generate_visualizations: Whether to generate plot images
        user_id: User ID for MinIO storage
        job_id: Job ID for MinIO storage
        
    Returns:
        Dictionary with complete evaluation results and optional visualizations
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
    
    result = {
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
    
    # Generate visualizations if requested
    if generate_visualizations and HAS_VISUALIZATION:
        try:
            import matplotlib.pyplot as plt
            
            visualizations = []
            
            # ROC curve
            fig_roc = plot_roc_curve(roc_result.to_dict())
            if user_id and job_id:
                url = save_figure_to_minio(fig_roc, user_id, job_id, "roc_curve.png")
                visualizations.append({
                    "type": "roc_curve",
                    "url": url,
                    "title": "ROC Curve",
                    "description": f"AUC = {roc_result.auc:.3f} (95% CI: {roc_result.auc_ci_lower:.3f}-{roc_result.auc_ci_upper:.3f})",
                })
            plt.close(fig_roc)
            
            # PR curve
            fig_pr = plot_pr_curve(pr_result.to_dict())
            if user_id and job_id:
                url = save_figure_to_minio(fig_pr, user_id, job_id, "pr_curve.png")
                visualizations.append({
                    "type": "pr_curve",
                    "url": url,
                    "title": "Precision-Recall Curve",
                    "description": f"AUC-PR = {pr_result.auc_pr:.3f}",
                })
            plt.close(fig_pr)
            
            # Calibration curve
            fig_cal = plot_calibration_curve(cal_result.to_dict())
            if user_id and job_id:
                url = save_figure_to_minio(fig_cal, user_id, job_id, "calibration_curve.png")
                visualizations.append({
                    "type": "calibration_curve",
                    "url": url,
                    "title": "Calibration Curve",
                    "description": f"Brier score = {cal_result.brier_score:.3f}",
                })
            plt.close(fig_cal)
            
            # Threshold analysis
            fig_thresh = plot_threshold_analysis(roc_result.to_dict())
            if user_id and job_id:
                url = save_figure_to_minio(fig_thresh, user_id, job_id, "threshold_analysis.png")
                visualizations.append({
                    "type": "threshold_analysis",
                    "url": url,
                    "title": "Threshold Analysis",
                    "description": "Sensitivity, specificity, PPV, NPV vs threshold",
                })
            plt.close(fig_thresh)
            
            # Confusion matrix at optimal threshold
            optimal_thresh = roc_result.optimal_threshold
            y_pred = (y_scores >= optimal_thresh).astype(int)
            tp = int(np.sum((y_pred == 1) & (y_true == 1)))
            tn = int(np.sum((y_pred == 0) & (y_true == 0)))
            fp = int(np.sum((y_pred == 1) & (y_true == 0)))
            fn = int(np.sum((y_pred == 0) & (y_true == 1)))
            
            cm_dict = {"tp": tp, "tn": tn, "fp": fp, "fn": fn}
            fig_cm = plot_confusion_matrix(cm_dict)
            if user_id and job_id:
                url = save_figure_to_minio(fig_cm, user_id, job_id, "confusion_matrix.png")
                visualizations.append({
                    "type": "confusion_matrix",
                    "url": url,
                    "title": "Confusion Matrix",
                    "description": f"At optimal threshold = {optimal_thresh:.2f}",
                })
            plt.close(fig_cm)
            
            result["visualizations"] = visualizations
            
        except Exception as e:
            logger.error(f"Error generating classifier visualizations: {e}")
            result["visualization_error"] = str(e)
    
    return result


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


def compare_multiple_models(
    y_true: Union[np.ndarray, pd.Series, List],
    models: Dict[str, Union[np.ndarray, pd.Series, List]],
    correction: str = "bonferroni",
    alpha: float = 0.05,
    generate_visualizations: bool = False,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare 3+ models simultaneously with pairwise AUC comparisons.
    
    Performs:
    - Individual AUC with 95% CI for each model
    - Pairwise DeLong tests between all models
    - Multiple comparison correction (Bonferroni, Holm, BH)
    - Model ranking by AUC
    
    Args:
        y_true: True binary labels
        models: Dict mapping model names to predicted probabilities
            Example: {"LR": probs_lr, "XGB": probs_xgb, "RF": probs_rf}
        correction: Multiple comparison correction method
            - "bonferroni": Bonferroni correction (conservative)
            - "holm": Holm-Bonferroni (less conservative)
            - "bh": Benjamini-Hochberg FDR control
            - "none": No correction
        alpha: Significance level
        generate_visualizations: If True, generate comparison plots
        user_id: User ID for MinIO path
        job_id: Job ID for MinIO path
        
    Returns:
        Dictionary with:
        - model_rankings: List of models ranked by AUC
        - individual_aucs: AUC and CI for each model
        - pairwise_comparisons: All pairwise DeLong test results
        - comparison_matrix: P-value matrix
        - best_model: Recommended best model
        - interpretation: Human-readable summary
    
    Example:
        >>> result = compare_multiple_models(
        ...     y_true,
        ...     {"Logistic": lr_probs, "XGBoost": xgb_probs, "Random Forest": rf_probs}
        ... )
        >>> print(result["interpretation"])
    """
    y_true = np.asarray(y_true)
    model_names = list(models.keys())
    n_models = len(model_names)
    
    if n_models < 2:
        raise ValueError("Need at least 2 models to compare")
    
    # Compute individual AUCs
    analyzer = ROCAnalyzer(alpha=alpha)
    individual_aucs = {}
    
    for name, scores in models.items():
        scores_arr = np.asarray(scores)
        roc_result = analyzer.compute_roc(y_true, scores_arr)
        individual_aucs[name] = {
            "auc": float(roc_result.auc),
            "auc_ci_lower": float(roc_result.auc_ci_lower),
            "auc_ci_upper": float(roc_result.auc_ci_upper),
            "auc_se": float(roc_result.auc_se),
            "optimal_threshold": float(roc_result.optimal_threshold),
        }
    
    # Rank models by AUC
    model_rankings = sorted(
        individual_aucs.items(),
        key=lambda x: x[1]["auc"],
        reverse=True
    )
    model_rankings = [
        {
            "rank": i + 1,
            "model": name,
            "auc": data["auc"],
            "auc_ci": f"[{data['auc_ci_lower']:.3f}, {data['auc_ci_upper']:.3f}]"
        }
        for i, (name, data) in enumerate(model_rankings)
    ]
    
    # Pairwise DeLong tests
    delong = DeLongTest(alpha=alpha)
    pairwise_comparisons = []
    p_values = []
    
    for i in range(n_models):
        for j in range(i + 1, n_models):
            name1 = model_names[i]
            name2 = model_names[j]
            scores1 = np.asarray(models[name1])
            scores2 = np.asarray(models[name2])
            
            result = delong.compare(y_true, scores1, scores2)
            
            pairwise_comparisons.append({
                "model1": name1,
                "model2": name2,
                "auc1": float(result.auc1),
                "auc2": float(result.auc2),
                "difference": float(result.difference),
                "se_difference": float(result.se_difference),
                "z_statistic": float(result.z_statistic),
                "p_value": float(result.p_value),
                "p_value_raw": float(result.p_value),
            })
            p_values.append(result.p_value)
    
    # Apply multiple comparison correction
    n_comparisons = len(p_values)
    
    if correction == "bonferroni":
        adjusted_alpha = alpha / n_comparisons
        adjusted_p_values = [min(p * n_comparisons, 1.0) for p in p_values]
        
    elif correction == "holm":
        # Holm-Bonferroni step-down procedure
        indexed = [(p, i) for i, p in enumerate(p_values)]
        indexed.sort(key=lambda x: x[0])
        
        adjusted_p_values = [0.0] * n_comparisons
        for rank, (p, orig_idx) in enumerate(indexed):
            multiplier = n_comparisons - rank
            adjusted_p = min(p * multiplier, 1.0)
            adjusted_p_values[orig_idx] = adjusted_p
        adjusted_alpha = alpha
        
    elif correction == "bh":
        # Benjamini-Hochberg FDR control
        indexed = [(p, i) for i, p in enumerate(p_values)]
        indexed.sort(key=lambda x: x[0])
        
        adjusted_p_values = [0.0] * n_comparisons
        for rank, (p, orig_idx) in enumerate(indexed):
            multiplier = n_comparisons / (rank + 1)
            adjusted_p = min(p * multiplier, 1.0)
            adjusted_p_values[orig_idx] = adjusted_p
        adjusted_alpha = alpha
        
    else:  # no correction
        adjusted_p_values = p_values
        adjusted_alpha = alpha
    
    # Update pairwise comparisons with adjusted p-values
    for i, comp in enumerate(pairwise_comparisons):
        comp["p_value_adjusted"] = float(adjusted_p_values[i])
        comp["significant"] = adjusted_p_values[i] < adjusted_alpha
    
    # Create comparison matrix
    comparison_matrix = {name: {name2: None for name2 in model_names} for name in model_names}
    for comp in pairwise_comparisons:
        comparison_matrix[comp["model1"]][comp["model2"]] = comp["p_value_adjusted"]
        comparison_matrix[comp["model2"]][comp["model1"]] = comp["p_value_adjusted"]
    
    # Determine best model
    best_model = model_rankings[0]
    second_best = model_rankings[1] if len(model_rankings) > 1 else None
    
    # Check if best is significantly better than second best
    best_significantly_better = False
    if second_best:
        for comp in pairwise_comparisons:
            if (comp["model1"] == best_model["model"] and comp["model2"] == second_best["model"]) or \
               (comp["model2"] == best_model["model"] and comp["model1"] == second_best["model"]):
                best_significantly_better = comp["significant"]
                break
    
    # Generate interpretation
    significant_pairs = [c for c in pairwise_comparisons if c["significant"]]
    
    interpretation_lines = [
        f"## Multi-Model Comparison Results",
        f"",
        f"**Best Model**: {best_model['model']} (AUC = {best_model['auc']:.3f})",
        f"",
        f"### Rankings",
    ]
    for r in model_rankings:
        interpretation_lines.append(f"{r['rank']}. {r['model']}: AUC = {r['auc']:.3f} {r['auc_ci']}")
    
    interpretation_lines.append("")
    interpretation_lines.append(f"### Statistical Comparisons (correction: {correction})")
    
    if significant_pairs:
        interpretation_lines.append(f"**{len(significant_pairs)} significant difference(s) found:**")
        for pair in significant_pairs:
            better = pair["model1"] if pair["difference"] > 0 else pair["model2"]
            worse = pair["model2"] if pair["difference"] > 0 else pair["model1"]
            interpretation_lines.append(
                f"- {better} > {worse} (Δ = {abs(pair['difference']):.3f}, p = {pair['p_value_adjusted']:.4f})"
            )
    else:
        interpretation_lines.append("No significant differences found between models.")
    
    if best_significantly_better:
        interpretation_lines.append("")
        interpretation_lines.append(f"✅ **{best_model['model']}** is significantly better than the second-best model.")
    else:
        interpretation_lines.append("")
        interpretation_lines.append(f"⚠️ Top models are not significantly different - consider other factors.")
    
    return {
        "status": "success",
        "analysis_type": "multi_model_comparison",
        "n_models": n_models,
        "n_comparisons": n_comparisons,
        "correction_method": correction,
        "model_rankings": model_rankings,
        "individual_aucs": individual_aucs,
        "pairwise_comparisons": pairwise_comparisons,
        "comparison_matrix": comparison_matrix,
        "best_model": {
            "name": best_model["model"],
            "auc": best_model["auc"],
            "significantly_better": best_significantly_better,
        },
        "interpretation": "\n".join(interpretation_lines),
    }
    
    # Generate visualizations if requested
    if generate_visualizations and HAS_VISUALIZATION and user_id and job_id:
        try:
            from visualization.roc import plot_roc_curves_comparison
            
            # Compute full ROC results for each model for plotting
            roc_results = []
            model_names_list = list(models.keys())
            
            for name in model_names_list:
                scores = np.asarray(models[name])
                roc_result = analyzer.compute_roc(y_true, scores)
                roc_results.append(roc_result.to_dict())
            
            # Create multi-model comparison plot
            fig = plot_roc_curves_comparison(
                roc_results,
                labels=model_names_list,
                title=f"Multi-Model ROC Comparison ({n_models} models)"
            )
            
            # Save to MinIO
            url = save_figure_to_minio(
                fig,
                filename="multi_model_roc_comparison.png",
                user_id=user_id,
                job_id=job_id,
            )
            
            output = {
                "status": "success",
                "analysis_type": "multi_model_comparison",
                "n_models": n_models,
                "n_comparisons": n_comparisons,
                "correction_method": correction,
                "model_rankings": model_rankings,
                "individual_aucs": individual_aucs,
                "pairwise_comparisons": pairwise_comparisons,
                "comparison_matrix": comparison_matrix,
                "best_model": {
                    "name": best_model["model"],
                    "auc": best_model["auc"],
                    "significantly_better": best_significantly_better,
                },
                "interpretation": "\n".join(interpretation_lines),
                "visualizations": [{
                    "type": "multi_model_roc_comparison",
                    "url": url,
                    "title": f"ROC Comparison: {n_models} Models",
                }]
            }
            
            import matplotlib.pyplot as plt
            plt.close(fig)
            
            return output
            
        except Exception as e:
            logger.warning(f"Failed to generate multi-model ROC comparison visualization: {e}")
    
    return {
        "status": "success",
        "analysis_type": "multi_model_comparison",
        "n_models": n_models,
        "n_comparisons": n_comparisons,
        "correction_method": correction,
        "model_rankings": model_rankings,
        "individual_aucs": individual_aucs,
        "pairwise_comparisons": pairwise_comparisons,
        "comparison_matrix": comparison_matrix,
        "best_model": {
            "name": best_model["model"],
            "auc": best_model["auc"],
            "significantly_better": best_significantly_better,
        },
        "interpretation": "\n".join(interpretation_lines),
    }


def threshold_analysis(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    thresholds: Optional[List[float]] = None,
    target_metric: Optional[str] = None,
    target_value: Optional[float] = None,
    n_thresholds: int = 21,
) -> Dict[str, Any]:
    """
    Comprehensive threshold analysis for clinical decision support.
    
    Provides complete metrics at each threshold to support clinical decisions.
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        thresholds: Custom threshold values to analyze (optional)
        target_metric: Metric to optimize ('sensitivity', 'specificity', 'ppv', 'npv', 'f1')
        target_value: Target value for the metric (e.g., 0.95)
        n_thresholds: Number of thresholds if not specified (default 21: 0.0, 0.05, ..., 1.0)
        
    Returns:
        Dictionary with:
        - threshold_table: Complete metrics at each threshold
        - target_threshold: Threshold achieving target metric (if specified)
        - recommended_thresholds: Thresholds for common clinical scenarios
        - clinical_interpretation: Decision support text
        
    Example:
        >>> # Find threshold for 95% sensitivity (screening test)
        >>> result = threshold_analysis(
        ...     y_true, y_scores,
        ...     target_metric="sensitivity",
        ...     target_value=0.95
        ... )
        >>> print(f"Use threshold {result['target_threshold']['threshold']:.2f}")
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    n = len(y_true)
    n_pos = np.sum(y_true)
    n_neg = n - n_pos
    prevalence = n_pos / n
    
    # Generate thresholds if not provided
    if thresholds is None:
        thresholds = np.linspace(0, 1, n_thresholds).tolist()
    
    # Compute metrics at each threshold
    threshold_table = []
    
    for thresh in thresholds:
        y_pred = (y_scores >= thresh).astype(int)
        
        tp = np.sum((y_pred == 1) & (y_true == 1))
        tn = np.sum((y_pred == 0) & (y_true == 0))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))
        
        sensitivity = tp / n_pos if n_pos > 0 else 0
        specificity = tn / n_neg if n_neg > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        accuracy = (tp + tn) / n
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
        
        # Youden's J
        youden_j = sensitivity + specificity - 1
        
        # Diagnostic odds ratio
        if fp > 0 and fn > 0:
            dor = (tp * tn) / (fp * fn)
        else:
            dor = float('inf') if tp > 0 and tn > 0 else 0
        
        # Likelihood ratios
        lr_pos = sensitivity / (1 - specificity) if specificity < 1 else float('inf')
        lr_neg = (1 - sensitivity) / specificity if specificity > 0 else float('inf')
        
        # Number needed to screen/diagnose
        if ppv > 0:
            nns = 1 / ppv  # Number needed to screen
        else:
            nns = float('inf')
        
        threshold_table.append({
            "threshold": float(thresh),
            "sensitivity": float(sensitivity),
            "specificity": float(specificity),
            "ppv": float(ppv),
            "npv": float(npv),
            "accuracy": float(accuracy),
            "f1": float(f1),
            "youden_j": float(youden_j),
            "lr_positive": float(lr_pos) if lr_pos != float('inf') else None,
            "lr_negative": float(lr_neg) if lr_neg != float('inf') else None,
            "dor": float(dor) if dor != float('inf') else None,
            "nns": float(nns) if nns != float('inf') else None,
            "confusion_matrix": {"tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)},
        })
    
    # Find threshold for target metric
    target_threshold = None
    if target_metric and target_value is not None:
        metric_key = target_metric.lower()
        
        # Find threshold that achieves target
        candidates = []
        for row in threshold_table:
            if row[metric_key] >= target_value:
                candidates.append(row)
        
        if candidates:
            # For sensitivity, prefer lower threshold (more permissive)
            # For specificity, prefer higher threshold (more restrictive)
            if metric_key in ["sensitivity", "npv"]:
                target_row = max(candidates, key=lambda x: x["threshold"])
            else:
                target_row = min(candidates, key=lambda x: x["threshold"])
            
            target_threshold = {
                "threshold": target_row["threshold"],
                "achieved_value": target_row[metric_key],
                "target_metric": target_metric,
                "target_value": target_value,
                "trade_offs": {
                    "sensitivity": target_row["sensitivity"],
                    "specificity": target_row["specificity"],
                    "ppv": target_row["ppv"],
                    "npv": target_row["npv"],
                    "f1": target_row["f1"],
                },
            }
        else:
            # Target not achievable
            best_row = max(threshold_table, key=lambda x: x[metric_key])
            target_threshold = {
                "threshold": best_row["threshold"],
                "achieved_value": best_row[metric_key],
                "target_metric": target_metric,
                "target_value": target_value,
                "target_achieved": False,
                "message": f"Target {target_metric} of {target_value} not achievable. Best: {best_row[metric_key]:.3f}",
            }
    
    # Recommended thresholds for common scenarios
    # Youden's J maximum
    youden_optimal = max(threshold_table, key=lambda x: x["youden_j"])
    
    # F1 maximum
    f1_optimal = max(threshold_table, key=lambda x: x["f1"])
    
    # High sensitivity (>= 0.90) with best specificity
    high_sens_candidates = [r for r in threshold_table if r["sensitivity"] >= 0.90]
    high_sens_optimal = max(high_sens_candidates, key=lambda x: x["specificity"]) if high_sens_candidates else None
    
    # High specificity (>= 0.90) with best sensitivity
    high_spec_candidates = [r for r in threshold_table if r["specificity"] >= 0.90]
    high_spec_optimal = max(high_spec_candidates, key=lambda x: x["sensitivity"]) if high_spec_candidates else None
    
    recommended_thresholds = {
        "youden_optimal": {
            "threshold": youden_optimal["threshold"],
            "sensitivity": youden_optimal["sensitivity"],
            "specificity": youden_optimal["specificity"],
            "description": "Balances sensitivity and specificity (Youden's J)",
        },
        "f1_optimal": {
            "threshold": f1_optimal["threshold"],
            "f1": f1_optimal["f1"],
            "sensitivity": f1_optimal["sensitivity"],
            "specificity": f1_optimal["specificity"],
            "description": "Maximizes F1 score (precision-recall balance)",
        },
    }
    
    if high_sens_optimal:
        recommended_thresholds["high_sensitivity"] = {
            "threshold": high_sens_optimal["threshold"],
            "sensitivity": high_sens_optimal["sensitivity"],
            "specificity": high_sens_optimal["specificity"],
            "description": "For screening: ≥90% sensitivity with best specificity",
        }
    
    if high_spec_optimal:
        recommended_thresholds["high_specificity"] = {
            "threshold": high_spec_optimal["threshold"],
            "sensitivity": high_spec_optimal["sensitivity"],
            "specificity": high_spec_optimal["specificity"],
            "description": "For confirmation: ≥90% specificity with best sensitivity",
        }
    
    # Generate clinical interpretation
    interpretation_lines = [
        "## Threshold Analysis for Clinical Decision Support",
        "",
        f"**Dataset**: n = {n}, prevalence = {prevalence:.1%}",
        "",
        "### Recommended Thresholds",
        "",
        f"**General Purpose** (Youden): threshold = {youden_optimal['threshold']:.2f}",
        f"  - Sensitivity: {youden_optimal['sensitivity']:.1%}, Specificity: {youden_optimal['specificity']:.1%}",
        "",
    ]
    
    if high_sens_optimal:
        interpretation_lines.extend([
            f"**Screening Test** (≥90% sensitivity): threshold = {high_sens_optimal['threshold']:.2f}",
            f"  - Sensitivity: {high_sens_optimal['sensitivity']:.1%}, Specificity: {high_sens_optimal['specificity']:.1%}",
            f"  - NPV: {high_sens_optimal['npv']:.1%} (negative test rules out disease)",
            "",
        ])
    
    if high_spec_optimal:
        interpretation_lines.extend([
            f"**Confirmatory Test** (≥90% specificity): threshold = {high_spec_optimal['threshold']:.2f}",
            f"  - Sensitivity: {high_spec_optimal['sensitivity']:.1%}, Specificity: {high_spec_optimal['specificity']:.1%}",
            f"  - PPV: {high_spec_optimal['ppv']:.1%} (positive test rules in disease)",
            "",
        ])
    
    if target_threshold:
        interpretation_lines.extend([
            "### Your Target Analysis",
            f"Target: {target_metric} ≥ {target_value:.1%}",
            f"Recommended threshold: {target_threshold['threshold']:.2f}",
            "",
        ])
    
    return {
        "status": "success",
        "analysis_type": "threshold_analysis",
        "n_samples": n,
        "n_positive": int(n_pos),
        "prevalence": float(prevalence),
        "n_thresholds": len(threshold_table),
        "threshold_table": threshold_table,
        "target_threshold": target_threshold,
        "recommended_thresholds": recommended_thresholds,
        "clinical_interpretation": "\n".join(interpretation_lines),
    }


def generate_publication_report(
    y_true: Union[np.ndarray, pd.Series, List],
    y_scores: Union[np.ndarray, pd.Series, List],
    model_name: str = "The prediction model",
    outcome_name: str = "the outcome",
    threshold_method: str = "youden",
    alpha: float = 0.05,
    decimal_places: int = 2,
) -> Dict[str, Any]:
    """
    Generate publication-ready statistical report for model performance.
    
    Produces formatted text suitable for journal submission, including:
    - AUC with 95% confidence intervals
    - Optimal threshold and associated metrics with CIs
    - Calibration assessment
    - Results formatted per TRIPOD/PROBAST guidelines
    
    Args:
        y_true: True binary labels
        y_scores: Predicted probabilities
        model_name: Name of the model (e.g., "The XGBoost model")
        outcome_name: Name of the outcome (e.g., "30-day mortality")
        threshold_method: Method for optimal threshold ('youden', 'f1')
        alpha: Significance level for confidence intervals
        decimal_places: Number of decimal places for reporting
        
    Returns:
        Dictionary with:
        - results_text: Main results paragraph (copy-paste ready)
        - methods_text: Methods description
        - table_data: Data for Table X (model performance)
        - figure_data: Data for ROC curve figure
        - all_metrics: Complete metrics dictionary
    
    Example:
        >>> report = generate_publication_report(
        ...     y_true, y_scores,
        ...     model_name="The gradient boosting model",
        ...     outcome_name="30-day readmission"
        ... )
        >>> print(report["results_text"])
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    n = len(y_true)
    n_pos = int(np.sum(y_true))
    n_neg = n - n_pos
    prevalence = n_pos / n
    
    # Compute ROC
    analyzer = ROCAnalyzer(alpha=alpha)
    roc_result = analyzer.compute_roc(y_true, y_scores, threshold_method=threshold_method)
    
    # Compute PR
    pr_analyzer = PrecisionRecallAnalyzer()
    pr_result = pr_analyzer.compute(y_true, y_scores)
    
    # Compute calibration
    cal_analyzer = CalibrationAnalyzer(n_bins=10)
    cal_result = cal_analyzer.analyze(y_true, y_scores)
    
    # Get optimal threshold metrics
    optimal_thresh = roc_result.optimal_threshold
    y_pred = (y_scores >= optimal_thresh).astype(int)
    
    tp = np.sum((y_pred == 1) & (y_true == 1))
    tn = np.sum((y_pred == 0) & (y_true == 0))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    
    sensitivity = tp / n_pos if n_pos > 0 else 0
    specificity = tn / n_neg if n_neg > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    accuracy = (tp + tn) / n
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
    
    # Bootstrap CIs for sensitivity, specificity, PPV, NPV
    def bootstrap_ci(y_true, y_scores, metric_func, n_bootstrap=1000, ci=0.95):
        """Compute bootstrap CI for a metric."""
        n = len(y_true)
        metrics = []
        for _ in range(n_bootstrap):
            idx = np.random.randint(0, n, size=n)
            try:
                m = metric_func(y_true[idx], y_scores[idx])
                if np.isfinite(m):
                    metrics.append(m)
            except Exception:
                continue
        
        if len(metrics) < 100:
            return None, None
        
        lower = np.percentile(metrics, (1 - ci) / 2 * 100)
        upper = np.percentile(metrics, (1 + ci) / 2 * 100)
        return lower, upper
    
    # Bootstrap for key metrics
    def sens_func(yt, ys):
        yp = (ys >= optimal_thresh).astype(int)
        tp = np.sum((yp == 1) & (yt == 1))
        pos = np.sum(yt)
        return tp / pos if pos > 0 else 0
    
    def spec_func(yt, ys):
        yp = (ys >= optimal_thresh).astype(int)
        tn = np.sum((yp == 0) & (yt == 0))
        neg = np.sum(yt == 0)
        return tn / neg if neg > 0 else 0
    
    def ppv_func(yt, ys):
        yp = (ys >= optimal_thresh).astype(int)
        tp = np.sum((yp == 1) & (yt == 1))
        pred_pos = np.sum(yp)
        return tp / pred_pos if pred_pos > 0 else 0
    
    def npv_func(yt, ys):
        yp = (ys >= optimal_thresh).astype(int)
        tn = np.sum((yp == 0) & (yt == 0))
        pred_neg = np.sum(yp == 0)
        return tn / pred_neg if pred_neg > 0 else 0
    
    sens_ci = bootstrap_ci(y_true, y_scores, sens_func, n_bootstrap=500)
    spec_ci = bootstrap_ci(y_true, y_scores, spec_func, n_bootstrap=500)
    ppv_ci = bootstrap_ci(y_true, y_scores, ppv_func, n_bootstrap=500)
    npv_ci = bootstrap_ci(y_true, y_scores, npv_func, n_bootstrap=500)
    
    # Format numbers
    dp = decimal_places
    
    def fmt(val, ci_low=None, ci_high=None):
        if ci_low is not None and ci_high is not None:
            return f"{val:.{dp}f} (95% CI: {ci_low:.{dp}f}-{ci_high:.{dp}f})"
        return f"{val:.{dp}f}"
    
    # Generate results text
    auc_text = fmt(roc_result.auc, roc_result.auc_ci_lower, roc_result.auc_ci_upper)
    
    sens_text = fmt(sensitivity, sens_ci[0], sens_ci[1]) if sens_ci[0] else f"{sensitivity:.{dp}f}"
    spec_text = fmt(specificity, spec_ci[0], spec_ci[1]) if spec_ci[0] else f"{specificity:.{dp}f}"
    
    # Threshold method description
    if threshold_method == "youden":
        thresh_desc = "Youden's J statistic"
    elif threshold_method == "f1":
        thresh_desc = "maximum F1 score"
    else:
        thresh_desc = threshold_method
    
    results_text = f"""{model_name} achieved an area under the receiver operating characteristic curve (AUC) of {auc_text} for predicting {outcome_name}. Using {thresh_desc}, the optimal probability threshold was {optimal_thresh:.{dp}f}, yielding a sensitivity of {sens_text} and specificity of {spec_text}. At this threshold, the positive predictive value was {ppv:.{dp}f} and negative predictive value was {npv:.{dp}f}. The model showed {'good' if cal_result.well_calibrated else 'suboptimal'} calibration (Hosmer-Lemeshow p{'>' if cal_result.hosmer_lemeshow_pvalue > 0.05 else '<'}0.05, Brier score={cal_result.brier_score:.3f})."""

    methods_text = f"""We evaluated the discriminative ability of the prediction model using the area under the receiver operating characteristic curve (AUC) with 95% confidence intervals calculated using the DeLong method. Model calibration was assessed using the Hosmer-Lemeshow goodness-of-fit test and Brier score. The optimal probability threshold was determined using {thresh_desc}. Sensitivity, specificity, positive predictive value, and negative predictive value were calculated at the optimal threshold with 95% confidence intervals from 500 bootstrap resamples. Statistical analyses were performed using Python with scipy and numpy packages."""

    # Table data
    table_data = {
        "title": f"Table X. Performance of {model_name} for predicting {outcome_name}",
        "metrics": [
            {"metric": "Sample size", "value": f"n = {n}", "ci": ""},
            {"metric": "Events", "value": f"n = {n_pos} ({prevalence:.1%})", "ci": ""},
            {"metric": "AUC", "value": f"{roc_result.auc:.{dp}f}", "ci": f"{roc_result.auc_ci_lower:.{dp}f}-{roc_result.auc_ci_upper:.{dp}f}"},
            {"metric": "Optimal threshold", "value": f"{optimal_thresh:.{dp}f}", "ci": ""},
            {"metric": "Sensitivity", "value": f"{sensitivity:.{dp}f}", "ci": f"{sens_ci[0]:.{dp}f}-{sens_ci[1]:.{dp}f}" if sens_ci[0] else ""},
            {"metric": "Specificity", "value": f"{specificity:.{dp}f}", "ci": f"{spec_ci[0]:.{dp}f}-{spec_ci[1]:.{dp}f}" if spec_ci[0] else ""},
            {"metric": "PPV", "value": f"{ppv:.{dp}f}", "ci": f"{ppv_ci[0]:.{dp}f}-{ppv_ci[1]:.{dp}f}" if ppv_ci[0] else ""},
            {"metric": "NPV", "value": f"{npv:.{dp}f}", "ci": f"{npv_ci[0]:.{dp}f}-{npv_ci[1]:.{dp}f}" if npv_ci[0] else ""},
            {"metric": "Accuracy", "value": f"{accuracy:.{dp}f}", "ci": ""},
            {"metric": "F1 score", "value": f"{f1:.{dp}f}", "ci": ""},
            {"metric": "Brier score", "value": f"{cal_result.brier_score:.3f}", "ci": ""},
            {"metric": "H-L p-value", "value": f"{cal_result.hosmer_lemeshow_pvalue:.3f}", "ci": ""},
        ],
    }
    
    # Figure data for ROC curve
    roc_curve_data = []
    for point in roc_result.curve_points:
        roc_curve_data.append({
            "fpr": point.fpr,
            "tpr": point.tpr,
            "threshold": point.threshold,
        })
    
    figure_data = {
        "title": f"Figure X. Receiver operating characteristic curve for {model_name}",
        "roc_curve": roc_curve_data,
        "auc": roc_result.auc,
        "auc_ci": [roc_result.auc_ci_lower, roc_result.auc_ci_upper],
        "optimal_point": {
            "fpr": 1 - specificity,
            "tpr": sensitivity,
            "threshold": optimal_thresh,
        },
    }
    
    # All metrics
    all_metrics = {
        "n": n,
        "n_positive": n_pos,
        "n_negative": n_neg,
        "prevalence": prevalence,
        "auc": roc_result.auc,
        "auc_ci_lower": roc_result.auc_ci_lower,
        "auc_ci_upper": roc_result.auc_ci_upper,
        "auc_se": roc_result.auc_se,
        "auc_pr": pr_result.auc_pr,
        "average_precision": pr_result.average_precision,
        "optimal_threshold": optimal_thresh,
        "threshold_method": threshold_method,
        "sensitivity": sensitivity,
        "sensitivity_ci": sens_ci,
        "specificity": specificity,
        "specificity_ci": spec_ci,
        "ppv": ppv,
        "ppv_ci": ppv_ci,
        "npv": npv,
        "npv_ci": npv_ci,
        "accuracy": accuracy,
        "f1": f1,
        "brier_score": cal_result.brier_score,
        "hosmer_lemeshow_p": cal_result.hosmer_lemeshow_pvalue,
        "calibration_slope": cal_result.calibration_slope,
        "well_calibrated": cal_result.well_calibrated,
    }
    
    return {
        "status": "success",
        "analysis_type": "publication_report",
        "results_text": results_text,
        "methods_text": methods_text,
        "table_data": table_data,
        "figure_data": figure_data,
        "all_metrics": all_metrics,
    }

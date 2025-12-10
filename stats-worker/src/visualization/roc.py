"""
ROC/PR Curve Visualization Module

Provides plotting functions for classifier evaluation:
- ROC curves with AUC and confidence intervals
- Precision-Recall curves
- Calibration curves (reliability diagrams)
- Confusion matrix heatmaps
- Threshold analysis plots

Usage:
    from visualization.roc import plot_roc_curve, plot_pr_curve
    
    # Plot ROC curve from result
    fig = plot_roc_curve(roc_result)
    
    # Plot multiple ROC curves for comparison
    fig = plot_roc_curves_comparison([result1, result2])
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from .style import (
    apply_publication_style,
    ROC_COLORS,
    CLINICAL_COLORS,
    get_figure_with_style,
    style_roc_plot,
)
from .schemas import (
    VisualizationResult,
    VisualizationType,
    ROCVisualizationResult,
)
from .storage import save_figure_to_minio

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# ROC Curve
# =============================================================================

def plot_roc_curve(
    roc_result: Dict[str, Any],
    title: Optional[str] = "ROC Curve",
    show_ci: bool = True,
    show_optimal: bool = True,
    show_diagonal: bool = True,
    show_auc_text: bool = True,
    color: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Plot single ROC curve with AUC and confidence interval.
    
    Args:
        roc_result: ROC analysis result dict (from ROCCurveResult.to_dict())
        title: Plot title
        show_ci: Show AUC confidence interval in legend
        show_optimal: Mark optimal threshold point
        show_diagonal: Show diagonal reference line
        show_auc_text: Show AUC value in legend
        color: Curve color (default: blue)
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Extract curve data
    curve_data = roc_result.get('curve', [])
    if not curve_data:
        ax.text(0.5, 0.5, 'No ROC data available', ha='center', va='center')
        return fig
    
    fpr = [p.get('fpr', 0) for p in curve_data]
    tpr = [p.get('tpr', 0) for p in curve_data]
    
    # Get AUC info
    auc = roc_result.get('auc', 0)
    auc_ci = roc_result.get('auc_ci', {})
    auc_lower = auc_ci.get('lower', auc)
    auc_upper = auc_ci.get('upper', auc)
    
    # Set color
    curve_color = color or ROC_COLORS['curve']
    
    # Build label
    if show_auc_text:
        if show_ci:
            label = f"AUC = {auc:.3f} (95% CI: {auc_lower:.3f}-{auc_upper:.3f})"
        else:
            label = f"AUC = {auc:.3f}"
    else:
        label = "ROC Curve"
    
    # Plot ROC curve
    ax.plot(fpr, tpr, color=curve_color, linewidth=2, label=label)
    
    # Fill under curve
    ax.fill_between(fpr, tpr, alpha=0.15, color=curve_color)
    
    # Plot diagonal reference
    if show_diagonal:
        ax.plot([0, 1], [0, 1], linestyle='--', color=ROC_COLORS['diagonal'],
                linewidth=1, label='Random (AUC = 0.5)')
    
    # Mark optimal threshold
    if show_optimal:
        optimal_thresh = roc_result.get('optimal_threshold')
        if optimal_thresh is not None:
            # Find the point closest to optimal threshold
            optimal_point = None
            for p in curve_data:
                if abs(p.get('threshold', 0) - optimal_thresh) < 0.01:
                    optimal_point = p
                    break
            
            if optimal_point is None and curve_data:
                # Find closest
                min_diff = float('inf')
                for p in curve_data:
                    diff = abs(p.get('threshold', 0) - optimal_thresh)
                    if diff < min_diff:
                        min_diff = diff
                        optimal_point = p
            
            if optimal_point:
                opt_fpr = optimal_point.get('fpr', 0)
                opt_tpr = optimal_point.get('tpr', 0)
                ax.scatter([opt_fpr], [opt_tpr], s=100, color=ROC_COLORS['optimal'],
                          marker='o', zorder=10, label=f'Optimal (t={optimal_thresh:.2f})')
                
                # Add annotation
                sens = optimal_point.get('sensitivity', opt_tpr)
                spec = optimal_point.get('specificity', 1 - opt_fpr)
                ax.annotate(
                    f'Sens={sens:.2f}\nSpec={spec:.2f}',
                    xy=(opt_fpr, opt_tpr),
                    xytext=(opt_fpr + 0.1, opt_tpr - 0.1),
                    fontsize=9,
                    arrowprops=dict(arrowstyle='->', color='gray'),
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
                )
    
    # Style
    style_roc_plot(ax, title)
    ax.legend(loc='lower right', frameon=True)
    
    # Add sample size info
    n_pos = roc_result.get('n_positive', '?')
    n_neg = roc_result.get('n_negative', '?')
    ax.text(0.02, 0.02, f"n+ = {n_pos}, n- = {n_neg}",
            transform=ax.transAxes, fontsize=9, va='bottom')
    
    plt.tight_layout()
    return fig


def plot_roc_curves_comparison(
    roc_results: List[Dict[str, Any]],
    labels: Optional[List[str]] = None,
    title: Optional[str] = "ROC Curves Comparison",
    show_diagonal: bool = True,
    colors: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (8, 8),
    comparison_result: Optional[Dict[str, Any]] = None,
) -> plt.Figure:
    """
    Plot multiple ROC curves for comparison.
    
    Args:
        roc_results: List of ROC analysis result dicts
        labels: Labels for each curve
        title: Plot title
        show_diagonal: Show diagonal reference line
        colors: List of colors for each curve
        figsize: Figure size
        comparison_result: Optional DeLong test comparison result
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Default colors
    if colors is None:
        default_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
        ]
        colors = default_colors[:len(roc_results)]
    
    # Default labels
    if labels is None:
        labels = [f"Model {i+1}" for i in range(len(roc_results))]
    
    # Plot each ROC curve
    for idx, (roc_result, label, color) in enumerate(zip(roc_results, labels, colors)):
        curve_data = roc_result.get('curve', [])
        if not curve_data:
            continue
        
        fpr = [p.get('fpr', 0) for p in curve_data]
        tpr = [p.get('tpr', 0) for p in curve_data]
        auc = roc_result.get('auc', 0)
        
        curve_label = f"{label} (AUC = {auc:.3f})"
        ax.plot(fpr, tpr, color=color, linewidth=2, label=curve_label)
    
    # Diagonal reference
    if show_diagonal:
        ax.plot([0, 1], [0, 1], linestyle='--', color=ROC_COLORS['diagonal'],
                linewidth=1, label='Random')
    
    # Style
    style_roc_plot(ax, title)
    ax.legend(loc='lower right', frameon=True)
    
    # Add comparison result if provided
    if comparison_result:
        p_value = comparison_result.get('p_value', 1)
        diff = comparison_result.get('difference', 0)
        
        if p_value < 0.001:
            p_text = f"ΔA UC = {diff:.3f}, p < 0.001"
        else:
            p_text = f"ΔAUC = {diff:.3f}, p = {p_value:.3f}"
        
        ax.text(0.98, 0.02, p_text, transform=ax.transAxes,
                ha='right', va='bottom', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    return fig


# =============================================================================
# Precision-Recall Curve
# =============================================================================

def plot_pr_curve(
    pr_result: Dict[str, Any],
    title: Optional[str] = "Precision-Recall Curve",
    show_auc: bool = True,
    show_f1_optimal: bool = True,
    show_baseline: bool = True,
    baseline_precision: Optional[float] = None,
    color: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Plot Precision-Recall curve.
    
    Args:
        pr_result: Precision-Recall analysis result dict
        title: Plot title
        show_auc: Show AUC-PR in legend
        show_f1_optimal: Mark F1-optimal threshold point
        show_baseline: Show baseline (random classifier)
        baseline_precision: Baseline precision (default: class prevalence)
        color: Curve color
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Extract curve data
    curve_data = pr_result.get('curve', [])
    if not curve_data:
        ax.text(0.5, 0.5, 'No PR data available', ha='center', va='center')
        return fig
    
    recall = [p.get('recall', 0) for p in curve_data]
    precision = [p.get('precision', 0) for p in curve_data]
    
    # Get AUC-PR
    auc_pr = pr_result.get('auc_pr', 0)
    avg_precision = pr_result.get('average_precision', auc_pr)
    
    # Set color
    curve_color = color or CLINICAL_COLORS['primary']
    
    # Build label
    if show_auc:
        label = f"AUC-PR = {auc_pr:.3f}"
    else:
        label = "PR Curve"
    
    # Plot PR curve
    ax.plot(recall, precision, color=curve_color, linewidth=2, label=label)
    ax.fill_between(recall, precision, alpha=0.15, color=curve_color)
    
    # Baseline (random classifier)
    if show_baseline and baseline_precision is not None:
        ax.axhline(y=baseline_precision, linestyle='--', color='gray',
                   linewidth=1, label=f'Random ({baseline_precision:.2f})')
    
    # Mark F1-optimal point
    if show_f1_optimal:
        f1_thresh = pr_result.get('f1_optimal_threshold')
        f1_max = pr_result.get('f1_max')
        
        if f1_thresh is not None:
            # Find the point closest to F1-optimal threshold
            opt_point = None
            for p in curve_data:
                if abs(p.get('threshold', 0) - f1_thresh) < 0.01:
                    opt_point = p
                    break
            
            if opt_point:
                opt_recall = opt_point.get('recall', 0)
                opt_precision = opt_point.get('precision', 0)
                ax.scatter([opt_recall], [opt_precision], s=100, 
                          color=ROC_COLORS['optimal'], marker='o', zorder=10,
                          label=f'F1-optimal (F1={f1_max:.2f})')
    
    # Style
    ax.set_xlim([0, 1.02])
    ax.set_ylim([0, 1.02])
    ax.set_xlabel('Recall (Sensitivity)')
    ax.set_ylabel('Precision (PPV)')
    ax.set_aspect('equal')
    
    if title:
        ax.set_title(title)
    
    ax.legend(loc='lower left', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    return fig


# =============================================================================
# Calibration Curve
# =============================================================================

def plot_calibration_curve(
    calibration_result: Dict[str, Any],
    title: Optional[str] = "Calibration Curve",
    show_histogram: bool = True,
    show_reference: bool = True,
    show_metrics: bool = True,
    color: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Plot calibration curve (reliability diagram).
    
    Args:
        calibration_result: Calibration analysis result dict
        title: Plot title
        show_histogram: Show prediction distribution histogram
        show_reference: Show perfect calibration line
        show_metrics: Show Brier score and H-L test
        color: Curve color
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    if show_histogram:
        fig, (ax_main, ax_hist) = plt.subplots(
            2, 1, figsize=figsize,
            gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.05}
        )
    else:
        fig, ax_main = plt.subplots(figsize=figsize)
        ax_hist = None
    
    # Extract bin data
    bins = calibration_result.get('bins', [])
    if not bins:
        ax_main.text(0.5, 0.5, 'No calibration data available', ha='center', va='center')
        return fig
    
    # Get predicted and observed probabilities
    predicted_probs = [b.get('mean_predicted', 0) for b in bins]
    observed_probs = [b.get('fraction_positive', 0) for b in bins]
    bin_counts = [b.get('count', 0) for b in bins]
    
    # Set color
    curve_color = color or CLINICAL_COLORS['primary']
    
    # Plot perfect calibration line
    if show_reference:
        ax_main.plot([0, 1], [0, 1], linestyle='--', color='gray',
                     linewidth=1, label='Perfect calibration')
    
    # Plot calibration curve
    ax_main.plot(predicted_probs, observed_probs, marker='o', color=curve_color,
                 linewidth=2, markersize=8, label='Model')
    
    # Error bars or confidence regions could be added here
    
    # Style main axis
    ax_main.set_xlim([0, 1])
    ax_main.set_ylim([0, 1])
    ax_main.set_xlabel('Predicted Probability')
    ax_main.set_ylabel('Observed Frequency')
    ax_main.set_aspect('equal')
    
    if title:
        ax_main.set_title(title)
    
    ax_main.legend(loc='lower right', frameon=True)
    ax_main.spines['top'].set_visible(False)
    ax_main.spines['right'].set_visible(False)
    
    # Add metrics
    if show_metrics:
        brier = calibration_result.get('brier_score', 0)
        hl = calibration_result.get('hosmer_lemeshow', {})
        hl_p = hl.get('p_value', 1)
        
        metrics_text = f"Brier: {brier:.3f}"
        if hl_p < 0.05:
            metrics_text += f"\nH-L p = {hl_p:.3f} (poor calibration)"
        else:
            metrics_text += f"\nH-L p = {hl_p:.3f}"
        
        ax_main.text(0.02, 0.98, metrics_text, transform=ax_main.transAxes,
                     va='top', fontsize=10,
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Histogram of predictions
    if show_histogram and ax_hist is not None:
        # Bar for each bin
        bin_centers = predicted_probs
        bin_width = 1.0 / len(bins) * 0.8
        ax_hist.bar(bin_centers, bin_counts, width=bin_width, color=curve_color, alpha=0.7)
        ax_hist.set_xlim([0, 1])
        ax_hist.set_xlabel('')
        ax_hist.set_ylabel('Count')
        ax_hist.spines['top'].set_visible(False)
        ax_hist.spines['right'].set_visible(False)
    
    plt.tight_layout()
    return fig


# =============================================================================
# Confusion Matrix
# =============================================================================

def plot_confusion_matrix(
    confusion_matrix: Union[np.ndarray, List[List[int]], Dict[str, int]],
    labels: Optional[List[str]] = None,
    title: Optional[str] = "Confusion Matrix",
    normalize: bool = False,
    cmap: str = 'Blues',
    show_values: bool = True,
    show_percentages: bool = True,
    figsize: Tuple[float, float] = (8, 7),
) -> plt.Figure:
    """
    Plot confusion matrix as heatmap.
    
    Args:
        confusion_matrix: 2x2 matrix as array, list, or dict with keys tn/fp/fn/tp
        labels: Class labels [negative_class, positive_class]
        title: Plot title
        normalize: Normalize by row (true labels)
        cmap: Colormap name
        show_values: Show count values in cells
        show_percentages: Show percentages in cells
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Convert to numpy array
    if isinstance(confusion_matrix, dict):
        cm = np.array([
            [confusion_matrix.get('tn', 0), confusion_matrix.get('fp', 0)],
            [confusion_matrix.get('fn', 0), confusion_matrix.get('tp', 0)]
        ])
    else:
        cm = np.array(confusion_matrix)
    
    # Default labels
    if labels is None:
        labels = ['Negative', 'Positive']
    
    # Normalize if requested
    if normalize:
        cm_display = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    else:
        cm_display = cm
    
    # Plot heatmap
    im = ax.imshow(cm_display, interpolation='nearest', cmap=cmap, aspect='auto')
    
    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Count' if not normalize else 'Proportion', rotation=-90, va="bottom")
    
    # Axis labels
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=labels,
           yticklabels=labels,
           xlabel='Predicted Label',
           ylabel='True Label')
    
    # Rotate x labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add text annotations
    if show_values:
        thresh = cm_display.max() / 2.
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                if show_percentages and normalize:
                    text = f"{cm[i, j]}\n({cm_display[i, j]:.1%})"
                elif show_percentages:
                    row_total = cm[i, :].sum()
                    pct = cm[i, j] / row_total if row_total > 0 else 0
                    text = f"{cm[i, j]}\n({pct:.1%})"
                else:
                    text = f"{cm[i, j]}"
                
                ax.text(j, i, text, ha="center", va="center",
                        color="white" if cm_display[i, j] > thresh else "black",
                        fontsize=12)
    
    if title:
        ax.set_title(title)
    
    # Add metrics text
    tn, fp, fn, tp = cm.ravel()
    total = tn + fp + fn + tp
    accuracy = (tp + tn) / total if total > 0 else 0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    
    metrics_text = (f"Accuracy: {accuracy:.3f}\n"
                   f"Sensitivity: {sensitivity:.3f}\n"
                   f"Specificity: {specificity:.3f}\n"
                   f"PPV: {ppv:.3f}\n"
                   f"NPV: {npv:.3f}")
    
    ax.text(1.35, 0.5, metrics_text, transform=ax.transAxes, va='center',
            fontsize=10, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    return fig


# =============================================================================
# Threshold Analysis
# =============================================================================

def plot_threshold_analysis(
    roc_result: Dict[str, Any],
    title: Optional[str] = "Threshold Analysis",
    metrics: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (10, 6),
) -> plt.Figure:
    """
    Plot sensitivity, specificity, PPV, NPV vs threshold.
    
    Args:
        roc_result: ROC analysis result dict with curve points
        title: Plot title
        metrics: Which metrics to show (default: all)
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    curve_data = roc_result.get('curve', [])
    if not curve_data:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        return fig
    
    # Default metrics
    if metrics is None:
        metrics = ['sensitivity', 'specificity', 'ppv', 'npv']
    
    # Extract data
    thresholds = [p.get('threshold', 0) for p in curve_data]
    
    # Sort by threshold
    sorted_idx = np.argsort(thresholds)
    thresholds = np.array(thresholds)[sorted_idx]
    
    colors = {
        'sensitivity': '#1f77b4',
        'specificity': '#ff7f0e',
        'ppv': '#2ca02c',
        'npv': '#d62728',
    }
    
    labels = {
        'sensitivity': 'Sensitivity (TPR)',
        'specificity': 'Specificity (TNR)',
        'ppv': 'PPV (Precision)',
        'npv': 'NPV',
    }
    
    for metric in metrics:
        if metric in ['sensitivity', 'specificity', 'ppv', 'npv']:
            values = [curve_data[i].get(metric, 0) for i in sorted_idx]
            # Filter out None values
            valid_mask = [v is not None for v in values]
            t_valid = thresholds[valid_mask]
            v_valid = [v for v, m in zip(values, valid_mask) if m]
            
            if v_valid:
                ax.plot(t_valid, v_valid, color=colors.get(metric, 'gray'),
                       linewidth=2, label=labels.get(metric, metric))
    
    # Mark optimal threshold
    optimal_thresh = roc_result.get('optimal_threshold')
    if optimal_thresh is not None:
        ax.axvline(x=optimal_thresh, linestyle='--', color='gray',
                   linewidth=1, label=f'Optimal ({optimal_thresh:.2f})')
    
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.02])
    ax.set_xlabel('Classification Threshold')
    ax.set_ylabel('Metric Value')
    
    if title:
        ax.set_title(title)
    
    ax.legend(loc='center right', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


# =============================================================================
# High-Level Integration Functions
# =============================================================================

def create_roc_visualizations(
    roc_result: Dict[str, Any],
    pr_result: Optional[Dict[str, Any]] = None,
    calibration_result: Optional[Dict[str, Any]] = None,
    confusion_matrix: Optional[Dict[str, int]] = None,
    user_id: str = "default",
    job_id: str = "default",
    save_to_minio: bool = True,
) -> List[VisualizationResult]:
    """
    Create all ROC analysis visualizations.
    
    Convenience function to generate standard classifier evaluation plots.
    
    Args:
        roc_result: ROC analysis results
        pr_result: Optional Precision-Recall results
        calibration_result: Optional calibration results
        confusion_matrix: Optional confusion matrix dict
        user_id: User ID for MinIO path
        job_id: Job ID for MinIO path
        save_to_minio: Whether to save to MinIO
        
    Returns:
        List of VisualizationResult objects
    """
    visualizations = []
    
    # 1. ROC curve
    try:
        fig_roc = plot_roc_curve(roc_result)
        
        if save_to_minio:
            url = save_figure_to_minio(fig_roc, user_id, job_id, "roc_curve.png")
        else:
            url = ""
        
        auc = roc_result.get('auc', 0)
        auc_ci = roc_result.get('auc_ci', {})
        
        visualizations.append(ROCVisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url=url,
            title="ROC Curve",
            description=f"AUC = {auc:.3f} (95% CI: {auc_ci.get('lower', 0):.3f}-{auc_ci.get('upper', 0):.3f})",
            auc=auc,
            auc_ci_lower=auc_ci.get('lower'),
            auc_ci_upper=auc_ci.get('upper'),
            optimal_threshold=roc_result.get('optimal_threshold'),
        ))
        plt.close(fig_roc)
    except Exception as e:
        logger.error(f"Error creating ROC plot: {e}")
    
    # 2. Threshold analysis
    try:
        fig_thresh = plot_threshold_analysis(roc_result)
        
        if save_to_minio:
            url = save_figure_to_minio(fig_thresh, user_id, job_id, "threshold_analysis.png")
        else:
            url = ""
        
        visualizations.append(VisualizationResult(
            type=VisualizationType.THRESHOLD_ANALYSIS,
            url=url,
            title="Threshold Analysis",
            description="Sensitivity, specificity, PPV, NPV vs classification threshold",
        ))
        plt.close(fig_thresh)
    except Exception as e:
        logger.error(f"Error creating threshold analysis plot: {e}")
    
    # 3. PR curve
    if pr_result:
        try:
            fig_pr = plot_pr_curve(pr_result)
            
            if save_to_minio:
                url = save_figure_to_minio(fig_pr, user_id, job_id, "pr_curve.png")
            else:
                url = ""
            
            visualizations.append(VisualizationResult(
                type=VisualizationType.PR_CURVE,
                url=url,
                title="Precision-Recall Curve",
                description=f"AUC-PR = {pr_result.get('auc_pr', 0):.3f}",
                metadata={"auc_pr": pr_result.get('auc_pr')}
            ))
            plt.close(fig_pr)
        except Exception as e:
            logger.error(f"Error creating PR plot: {e}")
    
    # 4. Calibration curve
    if calibration_result:
        try:
            fig_cal = plot_calibration_curve(calibration_result)
            
            if save_to_minio:
                url = save_figure_to_minio(fig_cal, user_id, job_id, "calibration_curve.png")
            else:
                url = ""
            
            visualizations.append(VisualizationResult(
                type=VisualizationType.CALIBRATION_CURVE,
                url=url,
                title="Calibration Curve",
                description=f"Brier score = {calibration_result.get('brier_score', 0):.3f}",
                metadata={
                    "brier_score": calibration_result.get('brier_score'),
                    "well_calibrated": calibration_result.get('well_calibrated'),
                }
            ))
            plt.close(fig_cal)
        except Exception as e:
            logger.error(f"Error creating calibration plot: {e}")
    
    # 5. Confusion matrix
    if confusion_matrix:
        try:
            fig_cm = plot_confusion_matrix(confusion_matrix)
            
            if save_to_minio:
                url = save_figure_to_minio(fig_cm, user_id, job_id, "confusion_matrix.png")
            else:
                url = ""
            
            visualizations.append(VisualizationResult(
                type=VisualizationType.CONFUSION_MATRIX,
                url=url,
                title="Confusion Matrix",
                description="Classification performance at optimal threshold",
            ))
            plt.close(fig_cm)
        except Exception as e:
            logger.error(f"Error creating confusion matrix plot: {e}")
    
    return visualizations

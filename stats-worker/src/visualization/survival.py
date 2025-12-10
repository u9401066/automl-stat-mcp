"""
Survival Analysis Visualization Module

Provides plotting functions for survival analysis results:
- Kaplan-Meier survival curves
- Cumulative hazard plots
- Forest plots for Cox regression
- Risk tables

Uses lifelines for optimized plotting when available,
falls back to pure matplotlib implementation.

Usage:
    from visualization.survival import plot_kaplan_meier, plot_forest_plot
    
    # Plot KM curve from result
    fig = plot_kaplan_meier(km_results)
    
    # Plot forest plot from Cox regression
    fig = plot_forest_plot(cox_result)
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from .style import (
    apply_publication_style,
    SURVIVAL_COLORS,
    CLINICAL_COLORS,
    get_figure_with_style,
    style_survival_plot,
    style_forest_plot,
)
from .schemas import (
    VisualizationResult,
    VisualizationType,
    SurvivalVisualizationResult,
)
from .storage import save_figure_to_minio

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# Kaplan-Meier Curves
# =============================================================================

def plot_kaplan_meier(
    km_results: Union[Dict[str, Any], List[Dict[str, Any]]],
    title: Optional[str] = "Kaplan-Meier Survival Curve",
    xlabel: str = "Time",
    ylabel: str = "Survival Probability",
    show_ci: bool = True,
    show_censored: bool = True,
    show_median: bool = True,
    show_at_risk: bool = True,
    at_risk_times: Optional[List[float]] = None,
    colors: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (10, 8),
    log_rank_p: Optional[float] = None,
) -> plt.Figure:
    """
    Plot Kaplan-Meier survival curves.
    
    Args:
        km_results: Single KM result dict or list of results (from KaplanMeierResult.to_dict())
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        show_ci: Show 95% confidence intervals
        show_censored: Show censoring tick marks
        show_median: Show median survival line
        show_at_risk: Show number at risk table below plot
        at_risk_times: Specific times for at-risk table (auto if None)
        colors: List of colors for each group
        figsize: Figure size (width, height)
        log_rank_p: Log-rank test p-value to display
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    # Normalize input to list
    if isinstance(km_results, dict):
        km_results = [km_results]
    
    n_groups = len(km_results)
    
    # Set up colors
    if colors is None:
        color_list = [
            SURVIVAL_COLORS.get(f'group{i+1}', CLINICAL_COLORS['primary'])
            for i in range(n_groups)
        ]
    else:
        color_list = colors
    
    # Create figure with risk table if requested
    if show_at_risk:
        fig, (ax_main, ax_risk) = plt.subplots(
            2, 1, figsize=figsize,
            gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.05}
        )
    else:
        fig, ax_main = plt.subplots(figsize=figsize)
        ax_risk = None
    
    # Track max time for x-axis
    max_time = 0
    
    # Plot each group
    for idx, km_result in enumerate(km_results):
        color = color_list[idx % len(color_list)]
        group_name = km_result.get('group', f'Group {idx + 1}')
        
        # Extract survival curve data
        curve_data = km_result.get('survival_curve', [])
        if not curve_data:
            continue
        
        times = [p['time'] for p in curve_data]
        survivals = [p['survival'] for p in curve_data]
        ci_lower = [p.get('ci_lower', p['survival']) for p in curve_data]
        ci_upper = [p.get('ci_upper', p['survival']) for p in curve_data]
        
        max_time = max(max_time, max(times) if times else 0)
        
        # Build step plot coordinates
        step_times, step_survivals = _make_step_curve(times, survivals)
        
        # Plot main curve
        label = f"{group_name} (n={km_result.get('n_subjects', '?')})"
        ax_main.plot(step_times, step_survivals, color=color, linewidth=2, label=label)
        
        # Plot confidence interval
        if show_ci:
            step_times_ci, step_lower = _make_step_curve(times, ci_lower)
            _, step_upper = _make_step_curve(times, ci_upper)
            ax_main.fill_between(
                step_times_ci, step_lower, step_upper,
                alpha=0.2, color=color, step='post'
            )
        
        # Plot censoring marks
        if show_censored:
            censored_times = []
            censored_survivals = []
            for i, p in enumerate(curve_data):
                if p.get('censored', 0) > 0 and i > 0:
                    censored_times.append(p['time'])
                    censored_survivals.append(curve_data[i-1]['survival'] if i > 0 else 1.0)
            
            if censored_times:
                ax_main.scatter(
                    censored_times, censored_survivals,
                    marker='|', s=50, color=color, zorder=5
                )
    
    # Style the main plot
    style_survival_plot(ax_main, title)
    ax_main.set_xlabel(xlabel)
    ax_main.set_ylabel(ylabel)
    ax_main.set_xlim(left=0)
    ax_main.set_ylim(0, 1.05)
    
    # Add median survival line
    if show_median:
        ax_main.axhline(y=0.5, linestyle=':', color='gray', alpha=0.7, linewidth=1)
        ax_main.text(max_time * 0.98, 0.52, 'Median', ha='right', va='bottom',
                     fontsize=9, color='gray')
    
    # Add log-rank p-value if provided
    if log_rank_p is not None:
        if log_rank_p < 0.001:
            p_text = "Log-rank p < 0.001"
        else:
            p_text = f"Log-rank p = {log_rank_p:.3f}"
        ax_main.text(0.98, 0.02, p_text, transform=ax_main.transAxes,
                     ha='right', va='bottom', fontsize=11,
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Legend
    ax_main.legend(loc='lower left', frameon=True)
    
    # Number at risk table
    if show_at_risk and ax_risk is not None:
        _add_risk_table(ax_risk, km_results, at_risk_times, color_list, max_time)
    
    plt.tight_layout()
    return fig


def _make_step_curve(times: List[float], values: List[float]) -> Tuple[List[float], List[float]]:
    """Convert times and values to step function coordinates."""
    if not times:
        return [], []
    
    step_times = []
    step_values = []
    
    for i, (t, v) in enumerate(zip(times, values)):
        if i > 0:
            # Horizontal line from previous point
            step_times.append(t)
            step_values.append(values[i-1])
        # Vertical drop
        step_times.append(t)
        step_values.append(v)
    
    return step_times, step_values


def _add_risk_table(
    ax: plt.Axes,
    km_results: List[Dict],
    at_risk_times: Optional[List[float]],
    colors: List[str],
    max_time: float,
) -> None:
    """Add number at risk table below survival plot."""
    # Determine time points
    if at_risk_times is None:
        # Auto-generate ~5 time points
        at_risk_times = np.linspace(0, max_time, 6).tolist()
    
    ax.set_xlim(0, max_time)
    ax.set_ylim(0, len(km_results) + 1)
    ax.axis('off')
    
    # Add header
    ax.text(-0.02, len(km_results) + 0.5, "At Risk", transform=ax.transData,
            ha='right', va='center', fontsize=10, fontweight='bold')
    
    for idx, km_result in enumerate(km_results):
        group_name = km_result.get('group', f'Group {idx + 1}')
        curve_data = km_result.get('survival_curve', [])
        
        y_pos = len(km_results) - idx - 0.5
        
        # Group label
        ax.text(-0.02, y_pos, group_name[:15], transform=ax.transData,
                ha='right', va='center', fontsize=9, color=colors[idx % len(colors)])
        
        # Number at risk at each time point
        for t in at_risk_times:
            at_risk = _get_at_risk_at_time(curve_data, t)
            ax.text(t, y_pos, str(at_risk), ha='center', va='center', fontsize=9)


def _get_at_risk_at_time(curve_data: List[Dict], t: float) -> int:
    """Get number at risk at a specific time from curve data."""
    if not curve_data:
        return 0
    
    for i, p in enumerate(curve_data):
        if p['time'] > t:
            return curve_data[i-1].get('at_risk', 0) if i > 0 else curve_data[0].get('at_risk', 0)
    
    return curve_data[-1].get('at_risk', 0)


# =============================================================================
# Cumulative Hazard Plot
# =============================================================================

def plot_cumulative_hazard(
    km_results: Union[Dict[str, Any], List[Dict[str, Any]]],
    title: Optional[str] = "Nelson-Aalen Cumulative Hazard",
    xlabel: str = "Time",
    ylabel: str = "Cumulative Hazard",
    show_ci: bool = True,
    colors: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (10, 6),
) -> plt.Figure:
    """
    Plot cumulative hazard curves (Nelson-Aalen estimator).
    
    Cumulative hazard H(t) = -log(S(t)) where S(t) is survival function.
    
    Args:
        km_results: Single KM result dict or list of results
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        show_ci: Show 95% confidence intervals
        colors: List of colors for each group
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    # Normalize input to list
    if isinstance(km_results, dict):
        km_results = [km_results]
    
    n_groups = len(km_results)
    
    # Set up colors
    if colors is None:
        color_list = [
            SURVIVAL_COLORS.get(f'group{i+1}', CLINICAL_COLORS['primary'])
            for i in range(n_groups)
        ]
    else:
        color_list = colors
    
    fig, ax = plt.subplots(figsize=figsize)
    
    for idx, km_result in enumerate(km_results):
        color = color_list[idx % len(color_list)]
        group_name = km_result.get('group', f'Group {idx + 1}')
        
        curve_data = km_result.get('survival_curve', [])
        if not curve_data:
            continue
        
        times = [p['time'] for p in curve_data if p['survival'] > 0]
        survivals = [p['survival'] for p in curve_data if p['survival'] > 0]
        
        # Convert to cumulative hazard: H(t) = -log(S(t))
        cum_hazard = [-np.log(s) for s in survivals]
        
        # Build step coordinates
        step_times, step_hazard = _make_step_curve(times, cum_hazard)
        
        label = f"{group_name} (n={km_result.get('n_subjects', '?')})"
        ax.plot(step_times, step_hazard, color=color, linewidth=2, label=label)
        
        # CI for cumulative hazard
        if show_ci:
            ci_lower = [p.get('ci_upper', p['survival']) for p in curve_data if p['survival'] > 0]
            ci_upper = [p.get('ci_lower', p['survival']) for p in curve_data if p['survival'] > 0]
            
            hazard_lower = [-np.log(max(s, 0.001)) for s in ci_lower]
            hazard_upper = [-np.log(max(s, 0.001)) for s in ci_upper]
            
            step_times_ci, step_lower = _make_step_curve(times, hazard_lower)
            _, step_upper = _make_step_curve(times, hazard_upper)
            
            ax.fill_between(
                step_times_ci, step_lower, step_upper,
                alpha=0.2, color=color, step='post'
            )
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    
    if title:
        ax.set_title(title)
    
    ax.legend(loc='upper left', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    return fig


# =============================================================================
# Forest Plot (Hazard Ratios)
# =============================================================================

def plot_forest_plot(
    cox_result: Dict[str, Any],
    title: Optional[str] = "Forest Plot - Hazard Ratios",
    xlabel: str = "Hazard Ratio (95% CI)",
    show_reference_line: bool = True,
    log_scale: bool = True,
    figsize: Tuple[float, float] = (10, 6),
    sort_by: str = 'default',  # 'default', 'hr', 'pvalue', 'name'
) -> plt.Figure:
    """
    Plot forest plot for Cox regression hazard ratios.
    
    Args:
        cox_result: Cox regression result dict (from CoxRegressionResult.to_dict())
        title: Plot title
        xlabel: X-axis label
        show_reference_line: Show HR=1 reference line
        log_scale: Use log scale for x-axis
        figsize: Figure size
        sort_by: How to sort variables ('default', 'hr', 'pvalue', 'name')
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    coefficients = cox_result.get('coefficients', [])
    if not coefficients:
        # Create empty plot
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No coefficients to display', ha='center', va='center')
        return fig
    
    # Sort coefficients if requested
    if sort_by == 'hr':
        coefficients = sorted(coefficients, key=lambda x: x.get('hazard_ratio', 1))
    elif sort_by == 'pvalue':
        coefficients = sorted(coefficients, key=lambda x: x.get('p_value', 1))
    elif sort_by == 'name':
        coefficients = sorted(coefficients, key=lambda x: x.get('variable', ''))
    
    n_vars = len(coefficients)
    
    # Figure dimensions
    fig_width = figsize[0]
    fig_height = max(figsize[1], n_vars * 0.5 + 2)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    y_positions = list(range(n_vars - 1, -1, -1))
    
    for idx, coef in enumerate(coefficients):
        y = y_positions[idx]
        
        hr = coef.get('hazard_ratio', 1)
        hr_ci = coef.get('hr_ci', {})
        hr_lower = hr_ci.get('lower', hr * 0.8)
        hr_upper = hr_ci.get('upper', hr * 1.2)
        p_value = coef.get('p_value', 1)
        var_name = coef.get('variable', f'Var {idx + 1}')
        
        # Determine color based on significance
        if p_value < 0.05:
            if hr > 1:
                color = CLINICAL_COLORS['danger']  # Increased risk
            else:
                color = CLINICAL_COLORS['success']  # Decreased risk
        else:
            color = CLINICAL_COLORS['neutral']  # Not significant
        
        # Plot point estimate
        ax.scatter([hr], [y], s=100, color=color, zorder=10, marker='s')
        
        # Plot confidence interval
        ax.plot([hr_lower, hr_upper], [y, y], color=color, linewidth=2, zorder=5)
        
        # Add caps
        cap_height = 0.15
        ax.plot([hr_lower, hr_lower], [y - cap_height, y + cap_height], color=color, linewidth=2)
        ax.plot([hr_upper, hr_upper], [y - cap_height, y + cap_height], color=color, linewidth=2)
        
        # Variable name on left
        ax.text(-0.02, y, var_name, ha='right', va='center', fontsize=10,
                transform=ax.get_yaxis_transform())
        
        # HR and CI on right
        ci_text = f"{hr:.2f} ({hr_lower:.2f}-{hr_upper:.2f})"
        ax.text(1.02, y, ci_text, ha='left', va='center', fontsize=9,
                transform=ax.get_yaxis_transform())
        
        # P-value
        if p_value < 0.001:
            p_text = "p<0.001"
        else:
            p_text = f"p={p_value:.3f}"
        ax.text(1.25, y, p_text, ha='left', va='center', fontsize=9,
                transform=ax.get_yaxis_transform())
    
    # Reference line at HR=1
    if show_reference_line:
        ax.axvline(x=1, color='gray', linestyle='-', linewidth=1, zorder=1)
    
    # Set scale
    if log_scale:
        ax.set_xscale('log')
        # Nice tick marks
        ax.set_xticks([0.1, 0.25, 0.5, 1, 2, 4, 10])
        ax.set_xticklabels(['0.1', '0.25', '0.5', '1', '2', '4', '10'])
    
    ax.set_xlabel(xlabel)
    ax.set_ylim(-0.5, n_vars - 0.5)
    ax.set_yticks([])
    
    if title:
        ax.set_title(title)
    
    # Style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add header row
    ax.text(-0.02, n_vars + 0.5, "Variable", ha='right', va='center', fontsize=10,
            fontweight='bold', transform=ax.get_yaxis_transform())
    ax.text(1.02, n_vars + 0.5, "HR (95% CI)", ha='left', va='center', fontsize=10,
            fontweight='bold', transform=ax.get_yaxis_transform())
    ax.text(1.25, n_vars + 0.5, "P-value", ha='left', va='center', fontsize=10,
            fontweight='bold', transform=ax.get_yaxis_transform())
    
    # Add footer with model info
    n_subjects = cox_result.get('n_subjects', '?')
    n_events = cox_result.get('n_events', '?')
    ax.text(0.5, -0.1, f"n={n_subjects}, events={n_events}",
            ha='center', va='top', fontsize=9, transform=ax.transAxes)
    
    plt.tight_layout()
    return fig


# =============================================================================
# Hazard Ratio Plot (Single Variable)
# =============================================================================

def plot_hazard_ratio(
    hr: float,
    ci_lower: float,
    ci_upper: float,
    label: str = "Treatment",
    title: Optional[str] = "Hazard Ratio",
    reference_label: str = "Reference",
    figsize: Tuple[float, float] = (8, 3),
) -> plt.Figure:
    """
    Plot single hazard ratio with CI.
    
    Simple visualization for single HR comparison.
    
    Args:
        hr: Hazard ratio
        ci_lower: Lower CI bound
        ci_upper: Upper CI bound
        label: Label for the comparison group
        title: Plot title
        reference_label: Label for reference (HR=1)
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Determine color
    if ci_lower > 1:
        color = CLINICAL_COLORS['danger']  # Significantly higher
    elif ci_upper < 1:
        color = CLINICAL_COLORS['success']  # Significantly lower
    else:
        color = CLINICAL_COLORS['neutral']  # Not significant
    
    # Plot point and CI
    ax.scatter([hr], [0], s=150, color=color, zorder=10, marker='D')
    ax.plot([ci_lower, ci_upper], [0, 0], color=color, linewidth=3, zorder=5)
    
    # Caps
    ax.plot([ci_lower, ci_lower], [-0.1, 0.1], color=color, linewidth=2)
    ax.plot([ci_upper, ci_upper], [-0.1, 0.1], color=color, linewidth=2)
    
    # Reference line
    ax.axvline(x=1, color='gray', linestyle='--', linewidth=1.5, zorder=1)
    ax.text(1, 0.3, reference_label, ha='center', va='bottom', fontsize=10, color='gray')
    
    # Labels
    ax.text(hr, -0.3, f"HR = {hr:.2f}\n({ci_lower:.2f} - {ci_upper:.2f})",
            ha='center', va='top', fontsize=11, fontweight='bold')
    
    ax.set_xscale('log')
    ax.set_xlim(min(0.2, ci_lower * 0.8), max(5, ci_upper * 1.2))
    ax.set_ylim(-0.6, 0.5)
    ax.set_yticks([])
    
    ax.set_xlabel("Hazard Ratio")
    
    if title:
        ax.set_title(title)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    return fig


# =============================================================================
# High-Level Integration Functions
# =============================================================================

def create_survival_visualizations(
    km_results: Dict[str, Any],
    cox_result: Optional[Dict[str, Any]] = None,
    log_rank_p: Optional[float] = None,
    user_id: str = "default",
    job_id: str = "default",
    save_to_minio: bool = True,
) -> List[VisualizationResult]:
    """
    Create all survival analysis visualizations.
    
    Convenience function to generate standard survival plots.
    
    Args:
        km_results: KM analysis results
        cox_result: Optional Cox regression results
        log_rank_p: Optional log-rank p-value
        user_id: User ID for MinIO path
        job_id: Job ID for MinIO path
        save_to_minio: Whether to save to MinIO
        
    Returns:
        List of VisualizationResult objects
    """
    visualizations = []
    
    # Extract group results if nested
    if 'groups' in km_results:
        group_data = [km_results['groups'][g] for g in km_results['groups']]
    elif 'survival_curve' in km_results:
        group_data = [km_results]
    else:
        group_data = list(km_results.values()) if isinstance(km_results, dict) else km_results
    
    # 1. Kaplan-Meier curve
    try:
        fig_km = plot_kaplan_meier(group_data, log_rank_p=log_rank_p)
        
        if save_to_minio:
            from .storage import save_figure_to_minio
            url = save_figure_to_minio(fig_km, user_id, job_id, "kaplan_meier.png")
        else:
            url = ""
        
        visualizations.append(SurvivalVisualizationResult(
            type=VisualizationType.KAPLAN_MEIER,
            url=url,
            title="Kaplan-Meier Survival Curves",
            description=f"Log-rank p = {log_rank_p:.4f}" if log_rank_p else "Survival curves",
            p_value=log_rank_p,
        ))
        plt.close(fig_km)
    except Exception as e:
        logger.error(f"Error creating KM plot: {e}")
    
    # 2. Cumulative hazard
    try:
        fig_ch = plot_cumulative_hazard(group_data)
        
        if save_to_minio:
            url = save_figure_to_minio(fig_ch, user_id, job_id, "cumulative_hazard.png")
        else:
            url = ""
        
        visualizations.append(VisualizationResult(
            type=VisualizationType.CUMULATIVE_HAZARD,
            url=url,
            title="Nelson-Aalen Cumulative Hazard",
            description="Cumulative hazard function",
        ))
        plt.close(fig_ch)
    except Exception as e:
        logger.error(f"Error creating cumulative hazard plot: {e}")
    
    # 3. Forest plot from Cox regression
    if cox_result and cox_result.get('coefficients'):
        try:
            fig_forest = plot_forest_plot(cox_result)
            
            if save_to_minio:
                url = save_figure_to_minio(fig_forest, user_id, job_id, "forest_plot.png")
            else:
                url = ""
            
            # Get overall model p-value
            global_tests = cox_result.get('global_tests', {})
            lr_test = global_tests.get('likelihood_ratio', {})
            model_p = lr_test.get('p_value')
            
            visualizations.append(VisualizationResult(
                type=VisualizationType.FOREST_PLOT,
                url=url,
                title="Forest Plot - Cox Regression",
                description=f"Model likelihood ratio p = {model_p:.4f}" if model_p else "Hazard ratios with 95% CI",
                metadata={
                    "n_subjects": cox_result.get('n_subjects'),
                    "n_events": cox_result.get('n_events'),
                    "concordance": cox_result.get('model_fit', {}).get('concordance'),
                }
            ))
            plt.close(fig_forest)
        except Exception as e:
            logger.error(f"Error creating forest plot: {e}")
    
    return visualizations

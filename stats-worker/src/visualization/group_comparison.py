"""
Group Comparison Visualization Module

Provides plotting functions for statistical group comparisons:
- Box plots with p-values (t-test, Mann-Whitney)
- Violin plots with statistical annotations
- Bar charts with error bars and significance
- ANOVA results visualization
- Chi-square contingency heatmaps
- Correlation heatmaps

Integrates with statannotations for automatic p-value annotations.

Usage:
    from visualization.group_comparison import plot_group_comparison
    
    # Plot boxplot with p-value annotation
    fig = plot_group_comparison(
        df, x='treatment', y='outcome',
        test='t-test_ind'
    )
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import seaborn as sns

from .style import (
    apply_publication_style,
    CLINICAL_COLORS,
    get_figure_with_style,
)
from .schemas import (
    VisualizationResult,
    VisualizationType,
    GroupComparisonVisualizationResult,
)
from .storage import save_figure_to_minio

import logging
logger = logging.getLogger(__name__)

# Try to import statannotations for p-value annotations
try:
    from statannotations.Annotator import Annotator
    HAS_STATANNOTATIONS = True
except ImportError:
    HAS_STATANNOTATIONS = False
    logger.debug("statannotations not available - p-value annotations will be simplified")


# =============================================================================
# Color Palettes
# =============================================================================

GROUP_COLORS = {
    'palette': 'Set2',  # Colorblind-friendly
    'highlight': '#E41A1C',  # Red for significant
    'neutral': '#377EB8',  # Blue
    'positive': '#4DAF4A',  # Green
    'negative': '#984EA3',  # Purple
}


# =============================================================================
# Box Plot with Statistical Annotation
# =============================================================================

def plot_group_comparison(
    data: Union[pd.DataFrame, Dict[str, Any]],
    x: Optional[str] = None,
    y: Optional[str] = None,
    hue: Optional[str] = None,
    plot_type: str = "boxplot",
    test: str = "t-test_ind",
    pairs: Optional[List[Tuple]] = None,
    p_values: Optional[List[float]] = None,
    show_data_points: bool = True,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 6),
    palette: str = "Set2",
) -> plt.Figure:
    """
    Plot group comparison with statistical annotations.
    
    Supports boxplots, violin plots, and bar charts with p-value annotations.
    Automatically adds significance brackets using statannotations.
    
    Args:
        data: DataFrame or dict with group data
        x: Column for x-axis (group variable)
        y: Column for y-axis (numeric variable)
        hue: Optional column for color grouping
        plot_type: 'boxplot', 'violin', 'bar', or 'strip'
        test: Statistical test for annotation
            - 't-test_ind': Independent t-test
            - 't-test_paired': Paired t-test
            - 'Mann-Whitney': Mann-Whitney U
            - 'Wilcoxon': Wilcoxon signed-rank
            - 'Kruskal': Kruskal-Wallis (+ Dunn post-hoc)
        pairs: List of group pairs for comparison [(g1, g2), ...]
        p_values: Pre-computed p-values (if provided, skips statistical test)
        show_data_points: Overlay individual data points
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        figsize: Figure size
        palette: Color palette
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Handle dict input (convert to DataFrame)
    if isinstance(data, dict):
        # Assume dict of {group_name: values_array}
        df_data = []
        for group, values in data.items():
            for v in values:
                df_data.append({x or 'group': group, y or 'value': v})
        data = pd.DataFrame(df_data)
        if x is None:
            x = 'group'
        if y is None:
            y = 'value'
    
    # Create the base plot
    if plot_type == "boxplot":
        sns.boxplot(data=data, x=x, y=y, hue=hue, ax=ax, palette=palette)
        if show_data_points:
            sns.stripplot(data=data, x=x, y=y, hue=hue, ax=ax, 
                         color='black', alpha=0.5, size=4, dodge=True if hue else False)
    
    elif plot_type == "violin":
        sns.violinplot(data=data, x=x, y=y, hue=hue, ax=ax, palette=palette, inner="box")
        if show_data_points:
            sns.stripplot(data=data, x=x, y=y, hue=hue, ax=ax,
                         color='black', alpha=0.5, size=3, dodge=True if hue else False)
    
    elif plot_type == "bar":
        sns.barplot(data=data, x=x, y=y, hue=hue, ax=ax, palette=palette, 
                   errorbar='se', capsize=0.1)
    
    elif plot_type == "strip":
        sns.stripplot(data=data, x=x, y=y, hue=hue, ax=ax, palette=palette, size=6)
    
    else:
        raise ValueError(f"Unknown plot_type: {plot_type}")
    
    # Add statistical annotations
    if HAS_STATANNOTATIONS and pairs is not None:
        try:
            annotator = Annotator(ax, pairs, data=data, x=x, y=y, hue=hue)
            
            if p_values is not None:
                # Use pre-computed p-values
                annotator.set_pvalues(p_values)
            else:
                # Calculate p-values using specified test
                annotator.configure(test=test, text_format='star', loc='inside')
                annotator.apply_test()
            
            annotator.annotate()
            
        except Exception as e:
            logger.warning(f"Failed to add statistical annotations: {e}")
            # Fall back to manual annotation if available
            if p_values is not None:
                _add_manual_pvalue_annotations(ax, pairs, p_values, data, x, y)
    
    elif p_values is not None and pairs is not None:
        # Manual annotation without statannotations
        _add_manual_pvalue_annotations(ax, pairs, p_values, data, x, y)
    
    # Labels
    ax.set_xlabel(xlabel or x or '')
    ax.set_ylabel(ylabel or y or '')
    ax.set_title(title or f'{y} by {x}')
    
    # Remove duplicate legend entries if hue and show_data_points
    if hue and show_data_points:
        handles, labels = ax.get_legend_handles_labels()
        n_unique = len(data[hue].unique())
        ax.legend(handles[:n_unique], labels[:n_unique])
    
    plt.tight_layout()
    
    return fig


def _add_manual_pvalue_annotations(
    ax: plt.Axes,
    pairs: List[Tuple],
    p_values: List[float],
    data: pd.DataFrame,
    x: str,
    y: str,
):
    """Add p-value annotations manually without statannotations."""
    groups = data[x].unique().tolist()
    y_max = data[y].max()
    y_range = data[y].max() - data[y].min()
    
    for i, (pair, pval) in enumerate(zip(pairs, p_values)):
        # Get x positions
        x1 = groups.index(pair[0]) if pair[0] in groups else 0
        x2 = groups.index(pair[1]) if pair[1] in groups else 1
        
        # Draw bracket
        y_pos = y_max + y_range * (0.05 + i * 0.08)
        
        ax.plot([x1, x1, x2, x2], [y_pos - y_range*0.01, y_pos, y_pos, y_pos - y_range*0.01], 
                color='black', linewidth=1)
        
        # Add p-value text
        pval_text = _format_pvalue(pval)
        ax.text((x1 + x2) / 2, y_pos + y_range*0.01, pval_text,
                ha='center', va='bottom', fontsize=10)


def _format_pvalue(p: float) -> str:
    """Format p-value for display."""
    if p < 0.001:
        return '***'
    elif p < 0.01:
        return '**'
    elif p < 0.05:
        return '*'
    else:
        return 'ns'


# =============================================================================
# ANOVA Results Visualization
# =============================================================================

def plot_anova_results(
    group_stats: Dict[str, Dict],
    test_result: Optional[Dict] = None,
    post_hoc: Optional[List[Dict]] = None,
    title: str = "ANOVA Results",
    ylabel: str = "Value",
    figsize: Tuple[float, float] = (10, 6),
) -> plt.Figure:
    """
    Plot ANOVA results with group means and confidence intervals.
    
    Creates a bar chart with error bars showing group means and
    annotates with F-statistic, p-value, and effect size.
    
    Args:
        group_stats: Dict of {group_name: {mean, std, n, ...}}
        test_result: Dict with {statistic, p_value, effect_size, test_name}
        post_hoc: List of post-hoc comparison dicts
        title: Plot title
        ylabel: Y-axis label
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    groups = list(group_stats.keys())
    n_groups = len(groups)
    
    means = [group_stats[g].get('mean', 0) for g in groups]
    stds = [group_stats[g].get('std', 0) for g in groups]
    ns = [group_stats[g].get('n', 1) for g in groups]
    
    # Calculate standard errors
    ses = [s / np.sqrt(n) if n > 0 else 0 for s, n in zip(stds, ns)]
    
    # Bar positions
    x_pos = np.arange(n_groups)
    
    # Create bar plot
    colors = sns.color_palette("Set2", n_groups)
    bars = ax.bar(x_pos, means, yerr=ses, capsize=5, color=colors,
                  edgecolor='black', linewidth=1)
    
    # Add sample sizes on bars
    for i, (bar, n) in enumerate(zip(bars, ns)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + ses[i] + 0.02 * max(means),
                f'n={n}', ha='center', va='bottom', fontsize=9)
    
    # Add test result annotation
    if test_result:
        stat = test_result.get('statistic', 0)
        p = test_result.get('p_value', 1)
        effect = test_result.get('effect_size', 0)
        test_name = test_result.get('test_name', 'ANOVA')
        
        sig_text = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        
        annotation = f"{test_name}\nF = {stat:.2f}, p = {p:.4f} {sig_text}\nη² = {effect:.3f}"
        
        ax.text(0.95, 0.95, annotation, transform=ax.transAxes,
                ha='right', va='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Add post-hoc significance brackets
    if post_hoc and len(post_hoc) > 0:
        y_max = max(m + s for m, s in zip(means, ses))
        y_range = max(means) - min(means) if means else 1
        
        sig_pairs = [ph for ph in post_hoc if ph.get('p_value', 1) < 0.05]
        
        for i, ph in enumerate(sig_pairs[:5]):  # Limit to 5 brackets
            g1 = ph.get('group1', ph.get('groups', ('', ''))[0])
            g2 = ph.get('group2', ph.get('groups', ('', ''))[1])
            p = ph.get('p_value', 1)
            
            if g1 in groups and g2 in groups:
                x1 = groups.index(g1)
                x2 = groups.index(g2)
                y_pos = y_max + y_range * (0.1 + i * 0.08)
                
                ax.plot([x1, x1, x2, x2], 
                        [y_pos - 0.02*y_range, y_pos, y_pos, y_pos - 0.02*y_range],
                        color='black', linewidth=1)
                ax.text((x1 + x2) / 2, y_pos + 0.01*y_range, _format_pvalue(p),
                        ha='center', va='bottom', fontsize=9)
    
    # Labels
    ax.set_xticks(x_pos)
    ax.set_xticklabels(groups, rotation=45 if n_groups > 5 else 0, ha='right' if n_groups > 5 else 'center')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    
    plt.tight_layout()
    
    return fig


# =============================================================================
# Chi-Square / Contingency Table Visualization
# =============================================================================

def plot_contingency_heatmap(
    contingency_table: Union[pd.DataFrame, np.ndarray],
    row_labels: Optional[List[str]] = None,
    col_labels: Optional[List[str]] = None,
    test_result: Optional[Dict] = None,
    title: str = "Contingency Table",
    annot: bool = True,
    show_percentages: bool = True,
    cmap: str = "Blues",
    figsize: Tuple[float, float] = (8, 6),
) -> plt.Figure:
    """
    Plot chi-square contingency table as a heatmap.
    
    Shows observed frequencies with optional row/column percentages
    and annotates with chi-square test results.
    
    Args:
        contingency_table: 2D array or DataFrame with frequencies
        row_labels: Labels for rows
        col_labels: Labels for columns
        test_result: Dict with {chi2, p_value, cramers_v}
        title: Plot title
        annot: Show values in cells
        show_percentages: Show percentages alongside counts
        cmap: Colormap
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Convert to DataFrame if needed
    if isinstance(contingency_table, np.ndarray):
        if row_labels is None:
            row_labels = [f"Row {i+1}" for i in range(contingency_table.shape[0])]
        if col_labels is None:
            col_labels = [f"Col {j+1}" for j in range(contingency_table.shape[1])]
        df = pd.DataFrame(contingency_table, index=row_labels, columns=col_labels)
    else:
        df = contingency_table.copy()
    
    # Calculate percentages
    total = df.values.sum()
    
    if show_percentages:
        # Create annotation strings with count and percentage
        annot_data = df.copy().astype(str)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                count = df.iloc[i, j]
                pct = 100 * count / total if total > 0 else 0
                annot_data.iloc[i, j] = f"{count}\n({pct:.1f}%)"
    else:
        annot_data = True if annot else None
    
    # Create heatmap
    sns.heatmap(df, annot=annot_data if show_percentages else annot,
                fmt='' if show_percentages else 'd',
                cmap=cmap, ax=ax, cbar_kws={'label': 'Count'},
                linewidths=0.5, linecolor='white')
    
    # Add test result annotation
    if test_result:
        chi2 = test_result.get('chi2', test_result.get('statistic', 0))
        p = test_result.get('p_value', 1)
        cramers = test_result.get('cramers_v', test_result.get('effect_size', None))
        
        sig_text = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        
        if cramers is not None:
            annotation = f"χ² = {chi2:.2f}, p = {p:.4f} {sig_text}\nCramér's V = {cramers:.3f}"
        else:
            annotation = f"χ² = {chi2:.2f}, p = {p:.4f} {sig_text}"
        
        ax.text(1.02, 0.98, annotation, transform=ax.transAxes,
                ha='left', va='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.set_title(title)
    
    plt.tight_layout()
    
    return fig


def plot_categorical_comparison(
    data: pd.DataFrame,
    x: str,
    hue: str,
    normalize: str = 'index',  # 'index' (row), 'columns' (col), or None
    test_result: Optional[Dict] = None,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 6),
) -> plt.Figure:
    """
    Plot grouped bar chart for categorical variable comparison.
    
    Creates a grouped bar chart showing proportions of categories
    across groups, with chi-square test annotation.
    
    Args:
        data: DataFrame
        x: Categorical variable for x-axis
        hue: Categorical variable for grouping/coloring
        normalize: How to normalize ('index', 'columns', or None)
        test_result: Dict with chi-square test results
        title: Plot title
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create crosstab
    cross = pd.crosstab(data[x], data[hue], normalize=normalize if normalize else False)
    
    if normalize:
        cross = cross * 100  # Convert to percentage
    
    # Plot
    cross.plot(kind='bar', ax=ax, colormap='Set2', edgecolor='black', linewidth=0.5)
    
    # Add test result
    if test_result:
        chi2 = test_result.get('chi2', test_result.get('statistic', 0))
        p = test_result.get('p_value', 1)
        cramers = test_result.get('cramers_v', test_result.get('effect_size', None))
        
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        
        annotation = f"χ² = {chi2:.2f}, p = {p:.4f} {sig}"
        if cramers:
            annotation += f"\nCramér's V = {cramers:.3f}"
        
        ax.text(0.95, 0.95, annotation, transform=ax.transAxes,
                ha='right', va='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Labels
    ylabel = 'Percentage (%)' if normalize else 'Count'
    ax.set_ylabel(ylabel)
    ax.set_xlabel(x)
    ax.set_title(title or f'{x} by {hue}')
    ax.legend(title=hue)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig


# =============================================================================
# Correlation Heatmap
# =============================================================================

def plot_correlation_heatmap(
    corr_matrix: Union[pd.DataFrame, np.ndarray],
    labels: Optional[List[str]] = None,
    method: str = "pearson",
    mask_upper: bool = True,
    annot: bool = True,
    title: str = "Correlation Matrix",
    cmap: str = "RdBu_r",
    figsize: Tuple[float, float] = (10, 8),
    vmin: float = -1,
    vmax: float = 1,
) -> plt.Figure:
    """
    Plot correlation matrix as a heatmap.
    
    Args:
        corr_matrix: Correlation matrix (DataFrame or ndarray)
        labels: Variable labels
        method: Correlation method (for title annotation)
        mask_upper: Mask upper triangle
        annot: Show correlation values
        title: Plot title
        cmap: Colormap (RdBu_r for diverging)
        figsize: Figure size
        vmin, vmax: Color scale limits
        
    Returns:
        matplotlib Figure object
    """
    apply_publication_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Convert to DataFrame if needed
    if isinstance(corr_matrix, np.ndarray):
        if labels is None:
            labels = [f"Var{i+1}" for i in range(corr_matrix.shape[0])]
        corr_df = pd.DataFrame(corr_matrix, index=labels, columns=labels)
    else:
        corr_df = corr_matrix
    
    # Create mask for upper triangle
    mask = None
    if mask_upper:
        mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1)
    
    # Create heatmap
    sns.heatmap(
        corr_df,
        mask=mask,
        annot=annot,
        fmt='.2f',
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={'shrink': 0.8, 'label': f'{method.capitalize()} Correlation'},
        ax=ax,
    )
    
    ax.set_title(f"{title} ({method.capitalize()})")
    
    plt.tight_layout()
    
    return fig


# =============================================================================
# T-Test Visualization
# =============================================================================

def plot_ttest_result(
    group1_data: np.ndarray,
    group2_data: np.ndarray,
    group1_name: str = "Group 1",
    group2_name: str = "Group 2",
    test_result: Optional[Dict] = None,
    plot_type: str = "boxplot",
    title: Optional[str] = None,
    ylabel: str = "Value",
    figsize: Tuple[float, float] = (6, 6),
) -> plt.Figure:
    """
    Plot t-test comparison between two groups.
    
    Creates a visualization comparing two groups with statistical
    annotation showing t-statistic, p-value, and effect size.
    
    Args:
        group1_data: Data for group 1
        group2_data: Data for group 2
        group1_name: Label for group 1
        group2_name: Label for group 2
        test_result: Dict with {statistic, p_value, effect_size, test_name}
        plot_type: 'boxplot', 'violin', or 'bar'
        title: Plot title
        ylabel: Y-axis label
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    # Create DataFrame
    df = pd.DataFrame({
        'group': [group1_name] * len(group1_data) + [group2_name] * len(group2_data),
        'value': list(group1_data) + list(group2_data)
    })
    
    # Set up pairs
    pairs = [(group1_name, group2_name)]
    p_values = [test_result.get('p_value', 1)] if test_result else None
    
    fig = plot_group_comparison(
        data=df,
        x='group',
        y='value',
        plot_type=plot_type,
        pairs=pairs,
        p_values=p_values,
        title=title or f"{group1_name} vs {group2_name}",
        ylabel=ylabel,
        figsize=figsize,
    )
    
    # Add detailed test annotation
    if test_result:
        ax = fig.axes[0]
        stat = test_result.get('statistic', 0)
        p = test_result.get('p_value', 1)
        effect = test_result.get('effect_size', None)
        test_name = test_result.get('test_name', 't-test')
        
        annotation_lines = [f"{test_name}", f"t = {stat:.3f}, p = {p:.4f}"]
        if effect is not None:
            effect_name = test_result.get('effect_size_name', "Cohen's d")
            annotation_lines.append(f"{effect_name} = {effect:.3f}")
        
        ax.text(0.95, 0.95, '\n'.join(annotation_lines), transform=ax.transAxes,
                ha='right', va='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig


# =============================================================================
# High-Level Visualization Creator
# =============================================================================

def create_group_comparison_visualizations(
    comparison_result: Dict[str, Any],
    data: Optional[pd.DataFrame] = None,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    save_to_minio: bool = True,
) -> List[VisualizationResult]:
    """
    Create visualizations for group comparison results.
    
    Automatically generates appropriate plots based on the comparison result:
    - T-test/Mann-Whitney: Box plot with p-value bracket
    - ANOVA/Kruskal-Wallis: Bar chart with post-hoc annotations
    - Chi-square: Contingency heatmap
    
    Args:
        comparison_result: Result from compare_distributions or similar
        data: Original DataFrame (required for some plots)
        user_id: User ID for MinIO storage
        job_id: Job ID for MinIO storage
        save_to_minio: Whether to save figures to MinIO
        
    Returns:
        List of VisualizationResult objects
    """
    results = []
    
    try:
        # Extract test info
        main_test = comparison_result.get('main_test', {})
        test_name = main_test.get('test_name', '')
        p_value = main_test.get('p_value')
        statistic = main_test.get('statistic')
        details = main_test.get('details', {})
        effect_size = details.get('effect_size')
        
        group_stats = comparison_result.get('group_statistics', comparison_result.get('group_stats', {}))
        post_hoc = comparison_result.get('post_hoc', [])
        
        # Determine plot type based on test
        if 't-test' in test_name.lower() or 'mann-whitney' in test_name.lower():
            # Two-group comparison
            if group_stats:
                groups = list(group_stats.keys())
                if len(groups) == 2:
                    # Create box plot
                    fig = plot_anova_results(
                        group_stats=group_stats,
                        test_result={
                            'test_name': test_name,
                            'statistic': statistic,
                            'p_value': p_value,
                            'effect_size': effect_size or 0,
                        },
                        title=f"Group Comparison ({test_name})",
                    )
                    
                    viz_result = GroupComparisonVisualizationResult(
                        type=VisualizationType.BOXPLOT,
                        url="",
                        title=f"Group Comparison ({test_name})",
                        description=f"p = {p_value:.4f}" if p_value else "",
                        p_value=p_value,
                        effect_size=effect_size,
                        test_name=test_name,
                    )
                    
                    if save_to_minio and user_id and job_id:
                        url = save_figure_to_minio(fig, "group_comparison.png", user_id, job_id)
                        viz_result.url = url
                    
                    results.append(viz_result)
                    plt.close(fig)
        
        elif 'anova' in test_name.lower() or 'kruskal' in test_name.lower():
            # Multi-group comparison
            fig = plot_anova_results(
                group_stats=group_stats,
                test_result={
                    'test_name': test_name,
                    'statistic': statistic,
                    'p_value': p_value,
                    'effect_size': effect_size or 0,
                },
                post_hoc=post_hoc,
                title=f"Group Comparison ({test_name})",
            )
            
            viz_result = GroupComparisonVisualizationResult(
                type=VisualizationType.BAR_CHART,
                url="",
                title=f"ANOVA Results ({test_name})",
                description=f"F = {statistic:.2f}, p = {p_value:.4f}" if statistic and p_value else "",
                p_value=p_value,
                effect_size=effect_size,
                test_name=test_name,
            )
            
            if save_to_minio and user_id and job_id:
                url = save_figure_to_minio(fig, "anova_results.png", user_id, job_id)
                viz_result.url = url
            
            results.append(viz_result)
            plt.close(fig)
        
        elif 'chi' in test_name.lower():
            # Categorical comparison - need contingency table
            if 'contingency_table' in comparison_result:
                fig = plot_contingency_heatmap(
                    contingency_table=comparison_result['contingency_table'],
                    test_result={
                        'chi2': statistic,
                        'p_value': p_value,
                        'cramers_v': effect_size,
                    },
                    title="Chi-Square Test",
                )
                
                viz_result = GroupComparisonVisualizationResult(
                    type=VisualizationType.HEATMAP,
                    url="",
                    title="Chi-Square Contingency Table",
                    description=f"χ² = {statistic:.2f}, p = {p_value:.4f}" if statistic and p_value else "",
                    p_value=p_value,
                    effect_size=effect_size,
                    test_name=test_name,
                )
                
                if save_to_minio and user_id and job_id:
                    url = save_figure_to_minio(fig, "chisquare_heatmap.png", user_id, job_id)
                    viz_result.url = url
                
                results.append(viz_result)
                plt.close(fig)
    
    except Exception as e:
        logger.error(f"Failed to create group comparison visualizations: {e}")
    
    return results

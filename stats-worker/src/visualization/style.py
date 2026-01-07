"""
Visualization Style Module

Provides publication-ready matplotlib styles for statistical plots.

Usage:
    from visualization.style import apply_publication_style

    # Apply before creating figures
    apply_publication_style()

    fig, ax = plt.subplots()
    ax.plot(x, y)
    # Figure will have publication-quality styling
"""
import matplotlib

matplotlib.use('Agg')
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt

# =============================================================================
# Publication Style Configuration
# =============================================================================

PUBLICATION_STYLE: Dict[str, Any] = {
    # Figure
    'figure.figsize': (8, 6),
    'figure.dpi': 100,  # Display DPI (save DPI is separate)
    'figure.facecolor': 'white',
    'figure.edgecolor': 'white',
    'figure.autolayout': True,

    # Font - using system fonts for compatibility
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Helvetica', 'Arial', 'sans-serif'],
    'font.size': 12,

    # Axes
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.linewidth': 1.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.facecolor': 'white',
    'axes.edgecolor': 'black',
    'axes.labelcolor': 'black',
    'axes.prop_cycle': plt.cycler(color=[
        '#1f77b4',  # Blue
        '#ff7f0e',  # Orange
        '#2ca02c',  # Green
        '#d62728',  # Red
        '#9467bd',  # Purple
        '#8c564b',  # Brown
        '#e377c2',  # Pink
        '#7f7f7f',  # Gray
        '#bcbd22',  # Yellow-green
        '#17becf',  # Cyan
    ]),

    # Ticks
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.major.size': 5,
    'ytick.major.size': 5,
    'xtick.direction': 'out',
    'ytick.direction': 'out',

    # Legend
    'legend.fontsize': 11,
    'legend.frameon': True,
    'legend.framealpha': 0.9,
    'legend.edgecolor': 'gray',
    'legend.fancybox': False,

    # Lines
    'lines.linewidth': 2,
    'lines.markersize': 8,

    # Grid
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,

    # Save
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'savefig.edgecolor': 'white',
}


# =============================================================================
# Color Palettes
# =============================================================================

# Medical/Clinical color palette (colorblind-friendly)
CLINICAL_COLORS = {
    'primary': '#1f77b4',      # Blue - main result
    'secondary': '#ff7f0e',    # Orange - comparison
    'success': '#2ca02c',      # Green - positive outcome
    'danger': '#d62728',       # Red - negative outcome
    'warning': '#ffbb78',      # Light orange - caution
    'info': '#17becf',         # Cyan - informational
    'neutral': '#7f7f7f',      # Gray - baseline/reference
    'treatment': '#1f77b4',    # Blue - treatment group
    'control': '#ff7f0e',      # Orange - control group
}

# ROC curve colors
ROC_COLORS = {
    'curve': '#1f77b4',        # Blue
    'fill': '#aec7e8',         # Light blue
    'diagonal': '#7f7f7f',     # Gray
    'optimal': '#d62728',      # Red
    'ci': '#c5b0d5',           # Light purple
}

# Survival analysis colors
SURVIVAL_COLORS = {
    'group1': '#1f77b4',       # Blue
    'group2': '#ff7f0e',       # Orange
    'group3': '#2ca02c',       # Green
    'group4': '#d62728',       # Red
    'censored': '#7f7f7f',     # Gray
    'ci_fill': '#aec7e8',      # Light blue
}

# Significance levels
SIGNIFICANCE_COLORS = {
    'significant': '#2ca02c',   # Green
    'not_significant': '#7f7f7f',  # Gray
    'highly_significant': '#1f77b4',  # Blue
}


# =============================================================================
# Style Functions
# =============================================================================

def apply_publication_style(style: Optional[Dict[str, Any]] = None) -> None:
    """
    Apply publication-ready matplotlib style globally.

    Args:
        style: Optional custom style dict to override defaults

    Example:
        >>> apply_publication_style()
        >>> fig, ax = plt.subplots()  # Will use publication style
    """
    # Start with publication style
    final_style = PUBLICATION_STYLE.copy()

    # Override with custom style if provided
    if style:
        final_style.update(style)

    # Apply to matplotlib
    plt.rcParams.update(final_style)


def get_figure_with_style(
    nrows: int = 1,
    ncols: int = 1,
    figsize: Optional[tuple] = None,
    **kwargs
) -> tuple:
    """
    Create a new figure with publication style applied.

    Args:
        nrows: Number of subplot rows
        ncols: Number of subplot columns
        figsize: Optional figure size (width, height) in inches
        **kwargs: Additional arguments passed to plt.subplots()

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> fig, ax = get_figure_with_style()
        >>> ax.plot([1, 2, 3], [1, 4, 9])
    """
    apply_publication_style()

    if figsize is None:
        # Calculate figsize based on subplots
        base_width = 8
        base_height = 6
        figsize = (base_width * ncols, base_height * nrows)

    fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, **kwargs)
    return fig, ax


def style_roc_plot(ax: plt.Axes, title: Optional[str] = None) -> None:
    """
    Apply ROC-specific styling to an axes.

    Args:
        ax: Matplotlib axes object
        title: Optional title for the plot
    """
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel('False Positive Rate (1 - Specificity)')
    ax.set_ylabel('True Positive Rate (Sensitivity)')
    ax.set_aspect('equal')

    if title:
        ax.set_title(title)

    # Add diagonal reference line
    ax.plot([0, 1], [0, 1], linestyle='--', color=ROC_COLORS['diagonal'],
            linewidth=1, label='Random Classifier')


def style_survival_plot(ax: plt.Axes, title: Optional[str] = None) -> None:
    """
    Apply survival plot-specific styling to an axes.

    Args:
        ax: Matplotlib axes object
        title: Optional title for the plot
    """
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel('Time')
    ax.set_ylabel('Survival Probability')

    if title:
        ax.set_title(title)

    # Add horizontal line at median survival
    ax.axhline(y=0.5, linestyle=':', color='gray', alpha=0.5, linewidth=1)


def style_forest_plot(ax: plt.Axes, title: Optional[str] = None) -> None:
    """
    Apply forest plot-specific styling to an axes.

    Args:
        ax: Matplotlib axes object
        title: Optional title for the plot
    """
    ax.axvline(x=1, linestyle='-', color='gray', linewidth=1)  # HR=1 reference
    ax.set_xlabel('Hazard Ratio (95% CI)')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)

    if title:
        ax.set_title(title)


def add_significance_annotation(
    ax: plt.Axes,
    x1: float,
    x2: float,
    y: float,
    p_value: float,
    height: float = 0.02,
) -> None:
    """
    Add significance annotation bracket with p-value.

    Args:
        ax: Matplotlib axes object
        x1, x2: X positions for the bracket ends
        y: Y position for the bracket
        p_value: P-value to display
        height: Height of the bracket
    """
    # Format p-value
    if p_value < 0.001:
        p_text = "***"
    elif p_value < 0.01:
        p_text = "**"
    elif p_value < 0.05:
        p_text = "*"
    else:
        p_text = "ns"

    # Draw bracket
    ax.plot([x1, x1, x2, x2], [y, y + height, y + height, y],
            color='black', linewidth=1)

    # Add text
    ax.text((x1 + x2) / 2, y + height, p_text,
            ha='center', va='bottom', fontsize=11)


# =============================================================================
# Initialize
# =============================================================================

# Apply publication style on module import (optional, can be disabled)
# apply_publication_style()

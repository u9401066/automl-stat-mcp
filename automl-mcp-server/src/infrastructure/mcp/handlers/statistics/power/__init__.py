"""
Power Analysis Tools Package

Submodules:
    - ttest: T-test and Proportion power analysis
    - anova: ANOVA and Chi-square power analysis
    - survival: Survival analysis power
"""
from .anova import register_anova_power_tools
from .survival import register_survival_power_tools
from .ttest import register_ttest_power_tools


def register_power_tools(mcp, stats_client):
    """Register all power analysis tools."""
    register_ttest_power_tools(mcp, stats_client)
    register_anova_power_tools(mcp, stats_client)
    register_survival_power_tools(mcp, stats_client)


__all__ = ["register_power_tools"]

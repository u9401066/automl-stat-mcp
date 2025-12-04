"""
Statistics Tools Package

This package provides statistical analysis MCP tools organized by domain:
- eda: Exploratory Data Analysis and Auto-Analysis
- tableone: Clinical Table 1 generation
- survival: Kaplan-Meier, Cox regression
- propensity: Propensity Score Analysis
- roc: ROC/AUC Analysis and Calibration
- power: Power Analysis (T-test, Proportion, ANOVA, Chi-square, Survival)
"""

from .base import register_all_statistics_tools

__all__ = ["register_all_statistics_tools"]

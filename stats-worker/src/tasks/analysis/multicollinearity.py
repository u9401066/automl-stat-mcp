"""
Multicollinearity Detection Module

Compute Variance Inflation Factor (VIF) to detect multicollinearity.

Contains:
    - VIFResult: Single column VIF result
    - MulticollinearityAnalysis: Complete analysis result
    - compute_vif: Main VIF computation function
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .base import safe_round

logger = logging.getLogger(__name__)


@dataclass
class VIFResult:
    """VIF analysis result for a single column."""
    column: str
    vif: float
    tolerance: float  # 1/VIF
    has_multicollinearity: bool

    def to_dict(self) -> Dict:
        return {
            "column": self.column,
            "vif": safe_round(self.vif, 2),
            "tolerance": safe_round(self.tolerance, 4),
            "has_multicollinearity": self.has_multicollinearity,
        }


@dataclass
class MulticollinearityAnalysis:
    """Complete multicollinearity analysis."""
    columns: List[str]
    vif_results: List[VIFResult] = field(default_factory=list)
    condition_number: Optional[float] = None
    problematic_columns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "columns_analyzed": self.columns,
            "vif_results": [v.to_dict() for v in self.vif_results],
            "condition_number": safe_round(self.condition_number, 2),
            "problematic_columns": self.problematic_columns,
            "recommendations": self.recommendations,
        }


def compute_vif(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    vif_threshold: float = 5.0,
) -> MulticollinearityAnalysis:
    """
    Compute Variance Inflation Factor (VIF) for numeric columns.

    VIF interpretation:
    - VIF = 1: No correlation
    - VIF < 5: Moderate correlation (usually acceptable)
    - VIF >= 5: High correlation (may need attention)
    - VIF >= 10: Severe multicollinearity (problematic)

    Args:
        df: DataFrame with numeric columns
        columns: Columns to analyze (default: all numeric)
        vif_threshold: VIF threshold for flagging (default: 5)

    Returns:
        MulticollinearityAnalysis with VIF for each column
    """
    # Select numeric columns
    if columns:
        numeric_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    result = MulticollinearityAnalysis(columns=numeric_cols)

    if len(numeric_cols) < 2:
        result.recommendations.append("Need at least 2 numeric columns for VIF analysis")
        return result

    # Clean data
    clean_df = df[numeric_cols].dropna()

    if len(clean_df) < len(numeric_cols) + 1:
        result.recommendations.append("Insufficient data points for VIF calculation")
        return result

    # Standardize for numerical stability
    X = clean_df.values
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std == 0] = 1  # Avoid division by zero
    X_standardized = (X - X_mean) / X_std

    # Compute VIF for each column
    for i, col in enumerate(numeric_cols):
        vif = _compute_single_vif(X_standardized, i)
        tolerance = 1 / vif if vif > 0 else 0
        has_mc = vif >= vif_threshold

        vif_result = VIFResult(
            column=col,
            vif=vif,
            tolerance=tolerance,
            has_multicollinearity=has_mc,
        )
        result.vif_results.append(vif_result)

        if has_mc:
            result.problematic_columns.append(col)

    # Sort by VIF descending
    result.vif_results.sort(key=lambda x: x.vif, reverse=True)

    # Compute condition number
    try:
        result.condition_number = np.linalg.cond(X_standardized)
    except Exception:
        pass

    # Generate recommendations
    if result.problematic_columns:
        result.recommendations.append(
            f"⚠ High multicollinearity detected in: {', '.join(result.problematic_columns)}"
        )
        result.recommendations.append(
            "Consider: (1) Remove highly correlated variables, (2) Use PCA, (3) Use regularization (Ridge/Lasso)"
        )
    else:
        result.recommendations.append("✓ No severe multicollinearity detected (all VIF < threshold)")

    if result.condition_number and result.condition_number > 30:
        result.recommendations.append(
            f"⚠ High condition number ({result.condition_number:.0f}) indicates numerical instability"
        )

    return result


def _compute_single_vif(X: np.ndarray, col_idx: int) -> float:
    """Compute VIF for a single column."""
    try:
        # Get the column to predict
        y = X[:, col_idx]

        # Get other columns as predictors
        X_others = np.delete(X, col_idx, axis=1)

        # Add intercept
        X_design = np.column_stack([np.ones(len(y)), X_others])

        # Compute R-squared using linear regression
        # beta = (X'X)^(-1) X'y
        XtX = X_design.T @ X_design
        Xty = X_design.T @ y

        try:
            beta = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            beta = np.linalg.lstsq(X_design, y, rcond=None)[0]

        y_pred = X_design @ beta

        # R-squared
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        r_squared = max(0, min(r_squared, 0.9999))  # Clamp to avoid division by zero

        # VIF = 1 / (1 - R²)
        vif = 1 / (1 - r_squared)

        return vif

    except Exception as e:
        logger.warning(f"VIF calculation failed for column {col_idx}: {e}")
        return float('inf')

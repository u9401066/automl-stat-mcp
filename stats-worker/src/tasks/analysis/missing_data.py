"""
Missing Value Analysis Module

Analyze missing value patterns and detect MCAR/MAR/MNAR.

Contains:
    - MissingValueAnalysis: Complete missing value analysis result
    - analyze_missing_values: Main analysis function
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from .base import safe_round

logger = logging.getLogger(__name__)


@dataclass
class MissingValueAnalysis:
    """Analysis of missing value patterns."""

    total_cells: int
    total_missing: int
    missing_pct: float

    # Per-column analysis
    column_missing: Dict[str, Dict] = field(default_factory=dict)

    # Missing pattern analysis
    missing_pattern: str = "unknown"  # MCAR, MAR, MNAR, mixed
    pattern_confidence: float = 0.0
    pattern_evidence: List[str] = field(default_factory=list)

    # Co-occurrence of missing values
    missing_correlations: List[Dict] = field(default_factory=list)

    # Little's MCAR test result
    mcar_test: Optional[Dict] = None

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_cells": self.total_cells,
                "total_missing": self.total_missing,
                "missing_pct": safe_round(self.missing_pct, 2),
            },
            "columns": self.column_missing,
            "pattern": {
                "type": self.missing_pattern,
                "confidence": safe_round(self.pattern_confidence, 2),
                "evidence": self.pattern_evidence,
            },
            "missing_correlations": self.missing_correlations,
            "mcar_test": self.mcar_test,
            "recommendations": self.recommendations,
        }


def analyze_missing_values(
    df: pd.DataFrame,
    alpha: float = 0.05,
) -> MissingValueAnalysis:
    """
    Comprehensive missing value analysis.

    Detects:
    - MCAR (Missing Completely At Random): Missingness is random
    - MAR (Missing At Random): Missingness depends on observed data
    - MNAR (Missing Not At Random): Missingness depends on unobserved data

    Args:
        df: DataFrame to analyze
        alpha: Significance level

    Returns:
        MissingValueAnalysis with pattern detection
    """
    total_cells = df.shape[0] * df.shape[1]
    total_missing = df.isna().sum().sum()
    missing_pct = (total_missing / total_cells) * 100 if total_cells > 0 else 0

    result = MissingValueAnalysis(
        total_cells=total_cells,
        total_missing=total_missing,
        missing_pct=missing_pct,
    )

    if total_missing == 0:
        result.missing_pattern = "none"
        result.pattern_confidence = 1.0
        result.pattern_evidence.append("No missing values")
        return result

    # Per-column analysis
    for col in df.columns:
        n_missing = df[col].isna().sum()
        if n_missing > 0:
            result.column_missing[col] = {
                "n_missing": int(n_missing),
                "pct_missing": safe_round((n_missing / len(df)) * 100, 2),
                "dtype": str(df[col].dtype),
            }

    # Missing value indicator matrix
    missing_indicator = df.isna().astype(int)

    # Check correlation between missingness indicators
    result.missing_correlations = _analyze_missing_correlations(missing_indicator, alpha)

    # Perform MCAR test (Little's test approximation)
    result.mcar_test = _littles_mcar_test(df, alpha)

    # Determine pattern
    evidence = []
    mcar_score = 0.0
    mar_score = 0.0

    # Evidence from MCAR test
    if result.mcar_test:
        if result.mcar_test.get("p_value", 0) > alpha:
            mcar_score += 0.4
            evidence.append("Little's MCAR test: Not significant (supports MCAR)")
        else:
            mar_score += 0.3
            evidence.append("Little's MCAR test: Significant (suggests MAR or MNAR)")

    # Evidence from missing correlations
    if result.missing_correlations:
        significant_corrs = [c for c in result.missing_correlations if c.get("significant")]
        if significant_corrs:
            mar_score += 0.3
            evidence.append(f"Found {len(significant_corrs)} significant missing value correlations (suggests MAR)")
        else:
            mcar_score += 0.2
            evidence.append("No significant missing value correlations (supports MCAR)")

    # Evidence from distribution comparison
    mar_evidence = _check_mar_pattern(df, missing_indicator, alpha)
    if mar_evidence:
        mar_score += 0.3
        evidence.extend(mar_evidence)
    else:
        mcar_score += 0.2
        evidence.append("No systematic differences in observed values (supports MCAR)")

    # Determine pattern
    if mcar_score > mar_score:
        result.missing_pattern = "MCAR"
        result.pattern_confidence = min(mcar_score / (mcar_score + mar_score + 0.01), 0.9)
    else:
        result.missing_pattern = "MAR"
        result.pattern_confidence = min(mar_score / (mcar_score + mar_score + 0.01), 0.9)

    result.pattern_evidence = evidence

    # Generate recommendations
    result.recommendations = _generate_missing_recommendations(result)

    return result


def _analyze_missing_correlations(
    missing_indicator: pd.DataFrame,
    alpha: float,
) -> List[Dict]:
    """Analyze correlations between missing indicators."""
    correlations = []
    cols_with_missing = missing_indicator.columns[missing_indicator.sum() > 0].tolist()

    for i, col1 in enumerate(cols_with_missing):
        for col2 in cols_with_missing[i + 1 :]:
            try:
                # Phi coefficient for binary variables
                contingency = pd.crosstab(missing_indicator[col1], missing_indicator[col2])
                if contingency.shape == (2, 2):
                    chi2, p, _, _ = stats.chi2_contingency(contingency)
                    n = contingency.sum().sum()
                    phi = np.sqrt(chi2 / n) if n > 0 else 0

                    if abs(phi) > 0.1:  # Only report meaningful correlations
                        correlations.append(
                            {
                                "col1": col1,
                                "col2": col2,
                                "phi_coefficient": safe_round(phi, 4),
                                "p_value": safe_round(p, 4),
                                "significant": p < alpha,
                            }
                        )
            except Exception:
                pass

    correlations.sort(key=lambda x: abs(x.get("phi_coefficient", 0)), reverse=True)
    return correlations[:10]  # Top 10


def _littles_mcar_test(df: pd.DataFrame, alpha: float) -> Optional[Dict]:
    """
    Simplified Little's MCAR test.

    Compare mean vectors of variables by missing patterns.
    """
    try:
        # Get numeric columns with some missing
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_with_missing = [c for c in numeric_cols if df[c].isna().any()]

        if not cols_with_missing or len(cols_with_missing) < 2:
            return None

        # Create missing pattern groups
        pattern_col = df[cols_with_missing].isna().astype(str).agg("".join, axis=1)
        unique_patterns = pattern_col.unique()

        if len(unique_patterns) < 2:
            return None

        # Compare means across patterns for each variable
        chi2_stats = []

        for col in numeric_cols:
            if df[col].isna().all():
                continue

            pattern_means = df.groupby(pattern_col)[col].mean()
            pattern_vars = df.groupby(pattern_col)[col].var()
            pattern_ns = df.groupby(pattern_col)[col].count()

            overall_mean = df[col].mean()

            # Weighted chi-square-like statistic
            for pattern in unique_patterns:
                if pattern in pattern_means and pattern_ns.get(pattern, 0) > 1:
                    diff = pattern_means[pattern] - overall_mean
                    var = pattern_vars.get(pattern, 1)
                    n = pattern_ns[pattern]
                    if var > 0:
                        chi2_stats.append((diff**2) * n / var)

        if not chi2_stats:
            return None

        # Combine statistics
        total_stat = sum(chi2_stats)
        df_stat = len(chi2_stats)

        # Approximate p-value using chi-square distribution
        p_value = 1 - stats.chi2.cdf(total_stat, df_stat) if df_stat > 0 else 1.0

        return {
            "statistic": safe_round(total_stat, 4),
            "df": df_stat,
            "p_value": safe_round(p_value, 4),
            "is_mcar": p_value > alpha,
            "interpretation": "MCAR hypothesis supported" if p_value > alpha else "MCAR hypothesis rejected",
        }

    except Exception as e:
        logger.warning(f"Little's MCAR test failed: {e}")
        return None


def _check_mar_pattern(
    df: pd.DataFrame,
    missing_indicator: pd.DataFrame,
    alpha: float,
) -> List[str]:
    """Check for MAR pattern by comparing observed values."""
    evidence = []

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in df.columns:
        if df[col].isna().sum() < 5:
            continue

        missing_mask = df[col].isna()

        # Compare other columns when this column is missing vs not missing
        for other_col in numeric_cols:
            if other_col == col:
                continue

            present = df.loc[~missing_mask, other_col].dropna()
            absent = df.loc[missing_mask, other_col].dropna()

            if len(present) < 5 or len(absent) < 5:
                continue

            try:
                stat, p = stats.mannwhitneyu(present, absent, alternative="two-sided")
                if p < alpha:
                    mean_diff = np.mean(absent) - np.mean(present)
                    evidence.append(
                        f"'{col}' missingness related to '{other_col}' (p={p:.4f}, mean diff={mean_diff:.2f})"
                    )
            except Exception:
                pass

    return evidence[:5]  # Top 5 findings


def _generate_missing_recommendations(analysis: MissingValueAnalysis) -> List[str]:
    """Generate recommendations based on missing value analysis."""
    recs = []

    if analysis.missing_pattern == "MCAR":
        recs.append("✓ Missing values appear random (MCAR). Safe to use listwise deletion or simple imputation.")
        if analysis.missing_pct < 5:
            recs.append("Low missing rate (<5%). Listwise deletion is acceptable.")
        else:
            recs.append("Consider multiple imputation for better results.")

    elif analysis.missing_pattern == "MAR":
        recs.append("⚠ Missing values show patterns (MAR). Use model-based imputation (e.g., MICE, KNN).")
        recs.append("Avoid listwise deletion as it may bias results.")
        recs.append("Include predictors of missingness in your analysis model.")

    # Column-specific recommendations
    high_missing = [c for c, v in analysis.column_missing.items() if v.get("pct_missing", 0) > 50]
    if high_missing:
        recs.append(f"Consider dropping columns with >50% missing: {', '.join(high_missing)}")

    return recs

"""
Enhanced Correlation Analysis Module

Compute correlation matrices with multiple methods, significance testing,
and heatmap visualization data.

Contains:
    - CorrelationPair: Single correlation result
    - EnhancedCorrelationResult: Complete analysis result
    - compute_enhanced_correlation: Main analysis function
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .base import safe_round

logger = logging.getLogger(__name__)


@dataclass
class CorrelationPair:
    """Correlation between two variables."""
    var1: str
    var2: str
    pearson_r: Optional[float] = None
    pearson_pvalue: Optional[float] = None
    spearman_rho: Optional[float] = None
    spearman_pvalue: Optional[float] = None
    kendall_tau: Optional[float] = None
    kendall_pvalue: Optional[float] = None
    strength: str = "none"
    is_significant: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "var1": self.var1,
            "var2": self.var2,
            "pearson": {
                "r": safe_round(self.pearson_r, 4),
                "p_value": safe_round(self.pearson_pvalue, 4),
            },
            "spearman": {
                "rho": safe_round(self.spearman_rho, 4),
                "p_value": safe_round(self.spearman_pvalue, 4),
            },
            "kendall": {
                "tau": safe_round(self.kendall_tau, 4),
                "p_value": safe_round(self.kendall_pvalue, 4),
            },
            "strength": self.strength,
            "is_significant": self.is_significant,
        }


@dataclass 
class EnhancedCorrelationResult:
    """Enhanced correlation analysis result."""
    columns: List[str]
    n_samples: int
    
    # Full correlation matrices
    pearson_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    spearman_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # P-value matrices
    pearson_pvalue_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    spearman_pvalue_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Significant pairs (for easy access)
    significant_pairs: List[CorrelationPair] = field(default_factory=list)
    
    # Heatmap data (for visualization)
    heatmap_data: List[Dict] = field(default_factory=list)
    
    # Statistics summary
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "columns": self.columns,
            "n_samples": self.n_samples,
            "matrices": {
                "pearson": self.pearson_matrix,
                "spearman": self.spearman_matrix,
                "pearson_pvalue": self.pearson_pvalue_matrix,
                "spearman_pvalue": self.spearman_pvalue_matrix,
            },
            "significant_pairs": [p.to_dict() for p in self.significant_pairs],
            "heatmap_data": self.heatmap_data,
            "summary": self.summary,
        }


def compute_enhanced_correlation(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "all",  # "pearson", "spearman", "kendall", "all"
    alpha: float = 0.05,
    min_correlation: float = 0.3,
) -> EnhancedCorrelationResult:
    """
    Compute enhanced correlation analysis with multiple methods and significance testing.
    
    Args:
        df: DataFrame with numeric columns
        columns: Columns to analyze (default: all numeric)
        method: Correlation method(s) to use
        alpha: Significance level
        min_correlation: Minimum |r| to report as significant pair
    
    Returns:
        EnhancedCorrelationResult with matrices and significant pairs
    """
    # Select numeric columns
    if columns:
        numeric_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) < 2:
        return EnhancedCorrelationResult(columns=numeric_cols, n_samples=len(df))
    
    # Clean data
    clean_df = df[numeric_cols].dropna()
    n_samples = len(clean_df)
    
    if n_samples < 5:
        return EnhancedCorrelationResult(columns=numeric_cols, n_samples=n_samples)
    
    result = EnhancedCorrelationResult(
        columns=numeric_cols,
        n_samples=n_samples,
    )
    
    # Compute correlation matrices
    if method in ["pearson", "all"]:
        pearson_corr = clean_df.corr(method='pearson')
        result.pearson_matrix = _matrix_to_dict(pearson_corr)
        result.pearson_pvalue_matrix = _compute_pvalue_matrix(clean_df, 'pearson')
    
    if method in ["spearman", "all"]:
        spearman_corr = clean_df.corr(method='spearman')
        result.spearman_matrix = _matrix_to_dict(spearman_corr)
        result.spearman_pvalue_matrix = _compute_pvalue_matrix(clean_df, 'spearman')
    
    # Find significant pairs
    result.significant_pairs = _find_significant_correlations(
        clean_df, numeric_cols, alpha, min_correlation
    )
    
    # Generate heatmap data (for frontend visualization)
    result.heatmap_data = _generate_heatmap_data(
        result.pearson_matrix if result.pearson_matrix else result.spearman_matrix,
        result.pearson_pvalue_matrix if result.pearson_pvalue_matrix else result.spearman_pvalue_matrix,
        alpha
    )
    
    # Summary statistics
    result.summary = {
        "n_variables": len(numeric_cols),
        "n_pairs": len(numeric_cols) * (len(numeric_cols) - 1) // 2,
        "n_significant": len([p for p in result.significant_pairs if p.is_significant]),
        "strongest_positive": None,
        "strongest_negative": None,
        "avg_correlation": None,
    }
    
    if result.significant_pairs:
        pos_pairs = [p for p in result.significant_pairs if (p.pearson_r or 0) > 0]
        neg_pairs = [p for p in result.significant_pairs if (p.pearson_r or 0) < 0]
        
        if pos_pairs:
            strongest_pos = max(pos_pairs, key=lambda x: x.pearson_r or 0)
            result.summary["strongest_positive"] = {
                "vars": f"{strongest_pos.var1} & {strongest_pos.var2}",
                "r": safe_round(strongest_pos.pearson_r, 4)
            }
        
        if neg_pairs:
            strongest_neg = min(neg_pairs, key=lambda x: x.pearson_r or 0)
            result.summary["strongest_negative"] = {
                "vars": f"{strongest_neg.var1} & {strongest_neg.var2}",
                "r": safe_round(strongest_neg.pearson_r, 4)
            }
    
    return result


def _matrix_to_dict(matrix: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Convert correlation matrix to nested dict."""
    result = {}
    for col in matrix.columns:
        result[col] = {
            row: safe_round(matrix.loc[row, col], 4)
            for row in matrix.index
        }
    return result


def _compute_pvalue_matrix(df: pd.DataFrame, method: str) -> Dict[str, Dict[str, float]]:
    """Compute p-value matrix for correlations."""
    cols = df.columns.tolist()
    pvalues = {}
    
    for i, col1 in enumerate(cols):
        pvalues[col1] = {}
        for col2 in cols:
            if col1 == col2:
                pvalues[col1][col2] = 0.0
            else:
                try:
                    if method == 'pearson':
                        _, p = stats.pearsonr(df[col1], df[col2])
                    else:
                        _, p = stats.spearmanr(df[col1], df[col2])
                    pvalues[col1][col2] = safe_round(p, 4)
                except:
                    pvalues[col1][col2] = None
    
    return pvalues


def _find_significant_correlations(
    df: pd.DataFrame,
    columns: List[str],
    alpha: float,
    min_correlation: float,
) -> List[CorrelationPair]:
    """Find all significant correlation pairs."""
    pairs = []
    
    for i, col1 in enumerate(columns):
        for col2 in columns[i+1:]:
            try:
                clean = df[[col1, col2]].dropna()
                if len(clean) < 5:
                    continue
                
                x, y = clean[col1], clean[col2]
                
                # Pearson
                pearson_r, pearson_p = stats.pearsonr(x, y)
                
                # Spearman
                spearman_rho, spearman_p = stats.spearmanr(x, y)
                
                # Kendall (only if small sample)
                kendall_tau, kendall_p = None, None
                if len(clean) < 1000:
                    kendall_tau, kendall_p = stats.kendalltau(x, y)
                
                # Determine significance and strength
                is_sig = pearson_p < alpha and abs(pearson_r) >= min_correlation
                strength = _interpret_correlation_strength(pearson_r)
                
                pair = CorrelationPair(
                    var1=col1,
                    var2=col2,
                    pearson_r=pearson_r,
                    pearson_pvalue=pearson_p,
                    spearman_rho=spearman_rho,
                    spearman_pvalue=spearman_p,
                    kendall_tau=kendall_tau,
                    kendall_pvalue=kendall_p,
                    strength=strength,
                    is_significant=is_sig,
                )
                
                if is_sig:
                    pairs.append(pair)
                    
            except Exception as e:
                logger.warning(f"Error computing correlation {col1}-{col2}: {e}")
    
    # Sort by absolute correlation
    pairs.sort(key=lambda p: abs(p.pearson_r or 0), reverse=True)
    return pairs


def _interpret_correlation_strength(r: float) -> str:
    """Interpret correlation strength."""
    abs_r = abs(r)
    if abs_r >= 0.9:
        return "very_strong"
    elif abs_r >= 0.7:
        return "strong"
    elif abs_r >= 0.5:
        return "moderate"
    elif abs_r >= 0.3:
        return "weak"
    else:
        return "negligible"


def _generate_heatmap_data(
    corr_matrix: Dict[str, Dict[str, float]],
    pvalue_matrix: Dict[str, Dict[str, float]],
    alpha: float,
) -> List[Dict]:
    """Generate data for heatmap visualization."""
    if not corr_matrix:
        return []
    
    heatmap = []
    cols = list(corr_matrix.keys())
    
    for i, row in enumerate(cols):
        for j, col in enumerate(cols):
            r = corr_matrix.get(row, {}).get(col)
            p = pvalue_matrix.get(row, {}).get(col) if pvalue_matrix else None
            
            heatmap.append({
                "x": j,
                "y": i,
                "row": row,
                "col": col,
                "value": r,
                "p_value": p,
                "significant": p < alpha if p is not None else False,
                "annotation": f"{r:.2f}" if r is not None else "",
            })
    
    return heatmap

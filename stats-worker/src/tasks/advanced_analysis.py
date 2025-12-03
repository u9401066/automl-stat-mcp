"""
Advanced Statistical Analysis Module

Phase 1: Enhanced Analysis Capabilities
- 1.1 Enhanced Correlation Analysis with visualization data
- 1.2 Distribution Comparison Tests (KS, Levene, post-hoc)
- 1.3 Missing Value Analysis (MCAR/MAR/MNAR detection)
- 1.4 Multicollinearity Detection (VIF)
"""
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import warnings

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=FutureWarning)


def safe_round(value: Optional[float], decimals: int = 4) -> Optional[float]:
    """Round a value safely, returning None for NaN/Inf"""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


# =============================================================================
# 1.1 Enhanced Correlation Analysis
# =============================================================================

@dataclass
class CorrelationPair:
    """Correlation between two variables"""
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
    """Enhanced correlation analysis result"""
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
    """Convert correlation matrix to nested dict"""
    result = {}
    for col in matrix.columns:
        result[col] = {
            row: safe_round(matrix.loc[row, col], 4)
            for row in matrix.index
        }
    return result


def _compute_pvalue_matrix(df: pd.DataFrame, method: str) -> Dict[str, Dict[str, float]]:
    """Compute p-value matrix for correlations"""
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
    """Find all significant correlation pairs"""
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
    """Interpret correlation strength"""
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
    """Generate data for heatmap visualization"""
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


# =============================================================================
# 1.2 Distribution Comparison Tests
# =============================================================================

@dataclass
class DistributionComparisonResult:
    """Result of distribution comparison test"""
    test_name: str
    statistic: float
    p_value: float
    interpretation: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "test": self.test_name,
            "statistic": safe_round(self.statistic, 4),
            "p_value": safe_round(self.p_value, 4),
            "interpretation": self.interpretation,
            "details": self.details,
        }


@dataclass
class GroupComparisonResult:
    """Result of group comparison analysis"""
    groups: List[str]
    n_groups: int
    
    # Normality tests per group
    normality_tests: Dict[str, Dict] = field(default_factory=dict)
    
    # Homogeneity of variance
    variance_test: Optional[DistributionComparisonResult] = None
    
    # Main comparison test
    main_test: Optional[DistributionComparisonResult] = None
    
    # Post-hoc tests (if applicable)
    post_hoc_tests: List[Dict] = field(default_factory=list)
    
    # Descriptive stats per group
    group_stats: Dict[str, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "groups": self.groups,
            "n_groups": self.n_groups,
            "normality": self.normality_tests,
            "variance_test": self.variance_test.to_dict() if self.variance_test else None,
            "main_test": self.main_test.to_dict() if self.main_test else None,
            "post_hoc": self.post_hoc_tests,
            "group_statistics": self.group_stats,
        }


def compare_distributions(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> GroupComparisonResult:
    """
    Compare distributions of a numeric variable across groups.
    
    Automatically selects appropriate tests based on:
    - Number of groups (2 vs >2)
    - Normality of distributions
    - Homogeneity of variance
    
    Args:
        df: DataFrame
        numeric_col: Column with numeric values to compare
        group_col: Column with group labels
        alpha: Significance level
    
    Returns:
        GroupComparisonResult with all test results
    """
    # Get groups
    groups = df[group_col].dropna().unique().tolist()
    n_groups = len(groups)
    
    result = GroupComparisonResult(groups=groups, n_groups=n_groups)
    
    if n_groups < 2:
        return result
    
    # Get data per group
    group_data = {}
    for g in groups:
        data = df[df[group_col] == g][numeric_col].dropna()
        if len(data) >= 3:
            group_data[str(g)] = data.values
    
    if len(group_data) < 2:
        return result
    
    # Compute group statistics
    for g, data in group_data.items():
        result.group_stats[g] = {
            "n": len(data),
            "mean": safe_round(np.mean(data), 4),
            "std": safe_round(np.std(data, ddof=1), 4),
            "median": safe_round(np.median(data), 4),
            "min": safe_round(np.min(data), 4),
            "max": safe_round(np.max(data), 4),
        }
    
    # Normality tests per group
    all_normal = True
    for g, data in group_data.items():
        if len(data) >= 3:
            try:
                if len(data) < 50:
                    stat, p = stats.shapiro(data)
                    test_name = "Shapiro-Wilk"
                else:
                    stat, p = stats.normaltest(data)
                    test_name = "D'Agostino-Pearson"
                
                is_normal = p > alpha
                all_normal = all_normal and is_normal
                
                result.normality_tests[g] = {
                    "test": test_name,
                    "statistic": safe_round(stat, 4),
                    "p_value": safe_round(p, 4),
                    "is_normal": is_normal,
                }
            except Exception as e:
                result.normality_tests[g] = {"error": str(e)}
    
    # Homogeneity of variance (Levene's test)
    try:
        stat, p = stats.levene(*group_data.values())
        equal_variance = p > alpha
        result.variance_test = DistributionComparisonResult(
            test_name="Levene's test",
            statistic=stat,
            p_value=p,
            interpretation="Equal variances" if equal_variance else "Unequal variances",
            details={"equal_variance": equal_variance},
        )
    except Exception as e:
        logger.warning(f"Levene's test failed: {e}")
    
    # Main comparison test
    use_parametric = all_normal and (result.variance_test and result.variance_test.details.get("equal_variance", False))
    
    group_arrays = list(group_data.values())
    
    if n_groups == 2:
        # Two-group comparison
        g1, g2 = group_arrays[0], group_arrays[1]
        
        if use_parametric:
            stat, p = stats.ttest_ind(g1, g2)
            test_name = "Independent t-test"
            # Cohen's d
            pooled_std = np.sqrt(((len(g1)-1)*np.var(g1, ddof=1) + (len(g2)-1)*np.var(g2, ddof=1)) / (len(g1)+len(g2)-2))
            effect_size = abs(np.mean(g1) - np.mean(g2)) / pooled_std if pooled_std > 0 else 0
            effect_name = "Cohen's d"
        else:
            stat, p = stats.mannwhitneyu(g1, g2, alternative='two-sided')
            test_name = "Mann-Whitney U"
            # Rank-biserial correlation
            n1, n2 = len(g1), len(g2)
            effect_size = 1 - (2*stat)/(n1*n2)
            effect_name = "rank-biserial r"
        
        result.main_test = DistributionComparisonResult(
            test_name=test_name,
            statistic=stat,
            p_value=p,
            interpretation=_interpret_pvalue(p, alpha),
            details={
                "effect_size": safe_round(effect_size, 4),
                "effect_size_name": effect_name,
                "effect_interpretation": _interpret_effect(effect_size, effect_name),
            }
        )
    
    else:
        # Multi-group comparison
        if use_parametric:
            stat, p = stats.f_oneway(*group_arrays)
            test_name = "One-way ANOVA"
            # Eta-squared
            total_mean = np.mean([x for arr in group_arrays for x in arr])
            ss_between = sum(len(arr) * (np.mean(arr) - total_mean)**2 for arr in group_arrays)
            ss_total = sum((x - total_mean)**2 for arr in group_arrays for x in arr)
            effect_size = ss_between / ss_total if ss_total > 0 else 0
            effect_name = "η² (eta-squared)"
        else:
            stat, p = stats.kruskal(*group_arrays)
            test_name = "Kruskal-Wallis H"
            # Epsilon-squared
            n = sum(len(arr) for arr in group_arrays)
            effect_size = (stat - n_groups + 1) / (n - n_groups) if n > n_groups else 0
            effect_name = "ε² (epsilon-squared)"
        
        result.main_test = DistributionComparisonResult(
            test_name=test_name,
            statistic=stat,
            p_value=p,
            interpretation=_interpret_pvalue(p, alpha),
            details={
                "effect_size": safe_round(effect_size, 4),
                "effect_size_name": effect_name,
                "effect_interpretation": _interpret_effect(effect_size, effect_name),
            }
        )
        
        # Post-hoc tests if significant
        if p < alpha:
            result.post_hoc_tests = _compute_post_hoc(group_data, use_parametric, alpha)
    
    return result


def _interpret_pvalue(p: float, alpha: float) -> str:
    """Interpret p-value"""
    if p < 0.001:
        return "Highly significant (p < 0.001)"
    elif p < alpha:
        return f"Significant (p = {p:.4f})"
    else:
        return f"Not significant (p = {p:.4f})"


def _interpret_effect(effect: float, name: str) -> str:
    """Interpret effect size"""
    if "Cohen" in name or "r" in name:
        if abs(effect) >= 0.8:
            return "Large effect"
        elif abs(effect) >= 0.5:
            return "Medium effect"
        else:
            return "Small effect"
    else:  # Eta-squared or Epsilon-squared
        if effect >= 0.14:
            return "Large effect"
        elif effect >= 0.06:
            return "Medium effect"
        else:
            return "Small effect"


def _compute_post_hoc(
    group_data: Dict[str, np.ndarray],
    parametric: bool,
    alpha: float,
) -> List[Dict]:
    """Compute pairwise post-hoc comparisons"""
    post_hoc = []
    groups = list(group_data.keys())
    
    # Bonferroni correction
    n_comparisons = len(groups) * (len(groups) - 1) // 2
    corrected_alpha = alpha / n_comparisons if n_comparisons > 0 else alpha
    
    for i, g1 in enumerate(groups):
        for g2 in groups[i+1:]:
            data1, data2 = group_data[g1], group_data[g2]
            
            try:
                if parametric:
                    stat, p = stats.ttest_ind(data1, data2)
                    test = "t-test"
                else:
                    stat, p = stats.mannwhitneyu(data1, data2, alternative='two-sided')
                    test = "Mann-Whitney U"
                
                post_hoc.append({
                    "group1": g1,
                    "group2": g2,
                    "test": test,
                    "statistic": safe_round(stat, 4),
                    "p_value": safe_round(p, 4),
                    "p_adjusted": safe_round(min(p * n_comparisons, 1.0), 4),  # Bonferroni
                    "significant": p < corrected_alpha,
                    "mean_diff": safe_round(np.mean(data1) - np.mean(data2), 4),
                })
            except Exception as e:
                logger.warning(f"Post-hoc {g1} vs {g2} failed: {e}")
    
    return post_hoc


def ks_test_two_samples(
    sample1: np.ndarray,
    sample2: np.ndarray,
) -> DistributionComparisonResult:
    """
    Perform two-sample Kolmogorov-Smirnov test.
    
    Tests whether two samples come from the same distribution.
    """
    stat, p = stats.ks_2samp(sample1, sample2)
    
    return DistributionComparisonResult(
        test_name="Kolmogorov-Smirnov (2-sample)",
        statistic=stat,
        p_value=p,
        interpretation="Same distribution" if p > 0.05 else "Different distributions",
        details={
            "n1": len(sample1),
            "n2": len(sample2),
        }
    )


# =============================================================================
# 1.3 Missing Value Analysis
# =============================================================================

@dataclass
class MissingValueAnalysis:
    """Analysis of missing value patterns"""
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
    """Analyze correlations between missing indicators"""
    correlations = []
    cols_with_missing = missing_indicator.columns[missing_indicator.sum() > 0].tolist()
    
    for i, col1 in enumerate(cols_with_missing):
        for col2 in cols_with_missing[i+1:]:
            try:
                # Phi coefficient for binary variables
                contingency = pd.crosstab(missing_indicator[col1], missing_indicator[col2])
                if contingency.shape == (2, 2):
                    chi2, p, _, _ = stats.chi2_contingency(contingency)
                    n = contingency.sum().sum()
                    phi = np.sqrt(chi2 / n) if n > 0 else 0
                    
                    if abs(phi) > 0.1:  # Only report meaningful correlations
                        correlations.append({
                            "col1": col1,
                            "col2": col2,
                            "phi_coefficient": safe_round(phi, 4),
                            "p_value": safe_round(p, 4),
                            "significant": p < alpha,
                        })
            except:
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
        pattern_col = df[cols_with_missing].isna().astype(str).agg(''.join, axis=1)
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
                        chi2_stats.append((diff ** 2) * n / var)
        
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
    """Check for MAR pattern by comparing observed values"""
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
                stat, p = stats.mannwhitneyu(present, absent, alternative='two-sided')
                if p < alpha:
                    mean_diff = np.mean(absent) - np.mean(present)
                    evidence.append(
                        f"'{col}' missingness related to '{other_col}' (p={p:.4f}, mean diff={mean_diff:.2f})"
                    )
            except:
                pass
    
    return evidence[:5]  # Top 5 findings


def _generate_missing_recommendations(analysis: MissingValueAnalysis) -> List[str]:
    """Generate recommendations based on missing value analysis"""
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


# =============================================================================
# 1.4 Multicollinearity Detection (VIF)
# =============================================================================

@dataclass
class VIFResult:
    """VIF analysis result"""
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
    """Complete multicollinearity analysis"""
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
    except:
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
    """Compute VIF for a single column"""
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


# =============================================================================
# Convenience Functions for Integration
# =============================================================================

def run_enhanced_analysis(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
    include_vif: bool = True,
    include_missing_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Run all enhanced analyses on a DataFrame.
    
    Args:
        df: DataFrame to analyze
        target_column: Optional target column for group comparisons
        include_vif: Whether to include VIF analysis
        include_missing_analysis: Whether to include missing value analysis
    
    Returns:
        Dictionary with all analysis results
    """
    results = {}
    
    # Enhanced correlation analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2:
        corr_result = compute_enhanced_correlation(df, numeric_cols)
        results["correlation_analysis"] = corr_result.to_dict()
    
    # Missing value analysis
    if include_missing_analysis:
        missing_result = analyze_missing_values(df)
        results["missing_analysis"] = missing_result.to_dict()
    
    # VIF analysis
    if include_vif and len(numeric_cols) >= 2:
        vif_result = compute_vif(df, numeric_cols)
        results["multicollinearity"] = vif_result.to_dict()
    
    # Group comparisons (if target specified)
    if target_column and target_column in df.columns:
        if df[target_column].nunique() <= 10:  # Categorical target
            results["group_comparisons"] = {}
            for col in numeric_cols:
                if col != target_column:
                    try:
                        comp_result = compare_distributions(df, col, target_column)
                        results["group_comparisons"][col] = comp_result.to_dict()
                    except Exception as e:
                        logger.warning(f"Group comparison failed for {col}: {e}")
    
    return results

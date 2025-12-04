"""
Distribution Comparison Tests Module

Compare distributions across groups with automatic test selection.

Contains:
    - DistributionComparisonResult: Single test result
    - GroupComparisonResult: Complete group comparison
    - compare_distributions: Main comparison function
    - ks_test_two_samples: Kolmogorov-Smirnov test
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
class DistributionComparisonResult:
    """Result of distribution comparison test."""
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
    """Result of group comparison analysis."""
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


def ks_test_two_samples(
    sample1: np.ndarray,
    sample2: np.ndarray,
) -> DistributionComparisonResult:
    """
    Perform two-sample Kolmogorov-Smirnov test.
    
    Tests whether two samples come from the same distribution.
    
    Args:
        sample1: First sample
        sample2: Second sample
        
    Returns:
        DistributionComparisonResult with test results
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


def _interpret_pvalue(p: float, alpha: float) -> str:
    """Interpret p-value."""
    if p < 0.001:
        return "Highly significant (p < 0.001)"
    elif p < alpha:
        return f"Significant (p = {p:.4f})"
    else:
        return f"Not significant (p = {p:.4f})"


def _interpret_effect(effect: float, name: str) -> str:
    """Interpret effect size."""
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
    """Compute pairwise post-hoc comparisons."""
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

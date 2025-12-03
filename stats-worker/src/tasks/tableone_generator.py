"""
TableOne Generator Module

Generates publication-ready "Table 1" (baseline characteristics table)
commonly used in medical research papers.

Features:
- Automatic detection of categorical vs continuous variables
- Stratification by grouping variable
- Multiple statistical tests (t-test, Mann-Whitney, Chi-square, Fisher's exact)
- Non-normal distribution handling (median/IQR)
- Multiple output formats (Markdown, HTML, LaTeX, dict)
- Missing value reporting
- SMD (Standardized Mean Difference) calculation
"""
import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Literal
from dataclasses import dataclass, field
from enum import Enum
import warnings

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore', category=RuntimeWarning)


def safe_round(value: Optional[float], decimals: int = 2) -> Optional[float]:
    """Safely round a value, handling None and NaN."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


class VariableType(Enum):
    """Type of variable for Table 1."""
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    BINARY = "binary"


class TestType(Enum):
    """Statistical test types."""
    TTEST = "t-test"
    MANN_WHITNEY = "Mann-Whitney U"
    ANOVA = "ANOVA"
    KRUSKAL_WALLIS = "Kruskal-Wallis"
    CHI_SQUARE = "Chi-square"
    FISHER_EXACT = "Fisher's exact"
    NONE = "None"


@dataclass
class VariableStats:
    """Statistics for a single variable."""
    name: str
    var_type: VariableType
    
    # For continuous variables
    mean: Optional[float] = None
    std: Optional[float] = None
    median: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    
    # For categorical variables
    categories: Optional[Dict[str, int]] = None
    category_pcts: Optional[Dict[str, float]] = None
    
    # Common
    n: int = 0
    n_missing: int = 0
    missing_pct: float = 0.0
    
    # Group comparison
    test_type: Optional[TestType] = None
    test_statistic: Optional[float] = None
    p_value: Optional[float] = None
    
    # Effect size
    smd: Optional[float] = None  # Standardized Mean Difference
    
    def to_dict(self) -> Dict:
        result = {
            "name": self.name,
            "type": self.var_type.value,
            "n": self.n,
            "n_missing": self.n_missing,
            "missing_pct": safe_round(self.missing_pct, 1),
        }
        
        if self.var_type == VariableType.CONTINUOUS:
            result.update({
                "mean": safe_round(self.mean, 2),
                "std": safe_round(self.std, 2),
                "median": safe_round(self.median, 2),
                "q25": safe_round(self.q25, 2),
                "q75": safe_round(self.q75, 2),
                "min": safe_round(self.min_val, 2),
                "max": safe_round(self.max_val, 2),
            })
        elif self.var_type in [VariableType.CATEGORICAL, VariableType.BINARY]:
            result.update({
                "categories": self.categories,
                "category_percentages": {k: safe_round(v, 1) for k, v in (self.category_pcts or {}).items()},
            })
        
        if self.test_type:
            result["test"] = {
                "type": self.test_type.value,
                "statistic": safe_round(self.test_statistic, 3),
                "p_value": safe_round(self.p_value, 4),
            }
        
        if self.smd is not None:
            result["smd"] = safe_round(self.smd, 3)
        
        return result


@dataclass
class TableOneResult:
    """Complete Table 1 result."""
    title: str
    n_total: int
    n_groups: int
    group_names: List[str]
    group_sizes: Dict[str, int]
    
    # Variable statistics by group
    variables: List[str]
    overall_stats: Dict[str, VariableStats] = field(default_factory=dict)
    group_stats: Dict[str, Dict[str, VariableStats]] = field(default_factory=dict)
    
    # Configuration
    show_pvalue: bool = True
    show_smd: bool = False
    show_missing: bool = True
    
    # Metadata
    nonnormal_vars: List[str] = field(default_factory=list)
    categorical_vars: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "n_total": self.n_total,
            "n_groups": self.n_groups,
            "groups": {
                "names": self.group_names,
                "sizes": self.group_sizes,
            },
            "variables": self.variables,
            "overall": {k: v.to_dict() for k, v in self.overall_stats.items()},
            "by_group": {
                group: {var: stats.to_dict() for var, stats in var_stats.items()}
                for group, var_stats in self.group_stats.items()
            },
            "config": {
                "show_pvalue": self.show_pvalue,
                "show_smd": self.show_smd,
                "show_missing": self.show_missing,
            },
            "metadata": {
                "nonnormal_variables": self.nonnormal_vars,
                "categorical_variables": self.categorical_vars,
            },
        }
    
    def to_markdown(self) -> str:
        """Generate Markdown formatted table."""
        return _format_as_markdown(self)
    
    def to_html(self) -> str:
        """Generate HTML formatted table."""
        return _format_as_html(self)
    
    def to_latex(self) -> str:
        """Generate LaTeX formatted table."""
        return _format_as_latex(self)


class TableOneGenerator:
    """
    Generates publication-ready Table 1 (baseline characteristics table).
    
    Usage:
        generator = TableOneGenerator()
        result = generator.generate(
            df=data,
            groupby="treatment_group",
            columns=["age", "gender", "bmi"],
            categorical=["gender"],
            nonnormal=["bmi"],
            pval=True,
        )
        
        # Output formats
        print(result.to_markdown())
        print(result.to_dict())
    """
    
    def __init__(
        self,
        alpha: float = 0.05,
        min_category_count: int = 5,
        normality_threshold: float = 0.05,
    ):
        """
        Initialize TableOne generator.
        
        Args:
            alpha: Significance level for tests
            min_category_count: Minimum count per cell for Chi-square (use Fisher below)
            normality_threshold: p-value threshold for normality test
        """
        self.alpha = alpha
        self.min_category_count = min_category_count
        self.normality_threshold = normality_threshold
    
    def generate(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        nonnormal: Optional[List[str]] = None,
        groupby: Optional[str] = None,
        pval: bool = True,
        smd: bool = False,
        missing: bool = True,
        overall: bool = True,
        title: str = "Table 1. Baseline Characteristics",
    ) -> TableOneResult:
        """
        Generate Table 1.
        
        Args:
            df: Input DataFrame
            columns: Columns to include (default: all except groupby)
            categorical: Columns to treat as categorical
            continuous: Columns to treat as continuous
            nonnormal: Continuous columns to report as median [IQR]
            groupby: Column for stratification
            pval: Include p-values
            smd: Include standardized mean difference
            missing: Include missing value counts
            overall: Include overall column
            title: Table title
        
        Returns:
            TableOneResult with statistics and formatted output
        """
        # Determine columns to analyze
        if columns is None:
            columns = [c for c in df.columns if c != groupby]
        else:
            columns = [c for c in columns if c in df.columns and c != groupby]
        
        categorical = categorical or []
        continuous = continuous or []
        nonnormal = nonnormal or []
        
        # Auto-detect variable types for unspecified columns
        for col in columns:
            if col not in categorical and col not in continuous:
                if self._is_categorical(df[col]):
                    categorical.append(col)
                else:
                    continuous.append(col)
        
        # Auto-detect non-normal distributions
        auto_nonnormal = self._detect_nonnormal(df, continuous)
        nonnormal = list(set(nonnormal) | set(auto_nonnormal))
        
        # Get groups
        if groupby and groupby in df.columns:
            groups = df[groupby].dropna().unique().tolist()
            group_sizes = {str(g): int((df[groupby] == g).sum()) for g in groups}
        else:
            groups = []
            group_sizes = {}
        
        # Calculate statistics
        overall_stats = {}
        group_stats = {str(g): {} for g in groups}
        
        for col in columns:
            var_type = VariableType.CATEGORICAL if col in categorical else VariableType.CONTINUOUS
            is_nonnormal = col in nonnormal
            
            # Overall stats
            if overall:
                overall_stats[col] = self._calculate_stats(
                    df[col], col, var_type, is_nonnormal
                )
            
            # Group stats
            if groups:
                for g in groups:
                    group_data = df[df[groupby] == g][col]
                    group_stats[str(g)][col] = self._calculate_stats(
                        group_data, col, var_type, is_nonnormal
                    )
                
                # Calculate p-value if requested
                if pval and len(groups) >= 2:
                    p_val, test_type, test_stat = self._calculate_pvalue(
                        df, col, groupby, groups, var_type
                    )
                    # Store in overall or first group stats
                    target = overall_stats.get(col) or group_stats[str(groups[0])].get(col)
                    if target:
                        target.p_value = p_val
                        target.test_type = test_type
                        target.test_statistic = test_stat
                
                # Calculate SMD if requested (only for 2 groups)
                if smd and len(groups) == 2:
                    smd_val = self._calculate_smd(
                        df, col, groupby, groups, var_type
                    )
                    target = overall_stats.get(col) or group_stats[str(groups[0])].get(col)
                    if target:
                        target.smd = smd_val
        
        return TableOneResult(
            title=title,
            n_total=len(df),
            n_groups=len(groups),
            group_names=[str(g) for g in groups],
            group_sizes=group_sizes,
            variables=columns,
            overall_stats=overall_stats,
            group_stats=group_stats,
            show_pvalue=pval,
            show_smd=smd,
            show_missing=missing,
            nonnormal_vars=nonnormal,
            categorical_vars=categorical,
        )
    
    def _is_categorical(self, series: pd.Series) -> bool:
        """Determine if a series should be treated as categorical."""
        # Object/category dtypes are categorical
        if series.dtype == 'object' or series.dtype.name == 'category':
            return True
        
        # Boolean is categorical
        if series.dtype == 'bool':
            return True
        
        # Few unique values suggests categorical
        n_unique = series.nunique()
        n_total = len(series.dropna())
        
        if n_unique <= 2:
            return True
        if n_unique <= 10 and n_unique / n_total < 0.05:
            return True
        
        return False
    
    def _detect_nonnormal(
        self,
        df: pd.DataFrame,
        continuous_cols: List[str],
    ) -> List[str]:
        """Detect which continuous columns have non-normal distributions."""
        nonnormal = []
        
        for col in continuous_cols:
            data = df[col].dropna()
            if len(data) < 8:
                continue
            
            try:
                if len(data) < 5000:
                    _, p = stats.shapiro(data)
                else:
                    _, p = stats.normaltest(data)
                
                if p < self.normality_threshold:
                    nonnormal.append(col)
            except Exception:
                pass
        
        return nonnormal
    
    def _calculate_stats(
        self,
        data: pd.Series,
        name: str,
        var_type: VariableType,
        is_nonnormal: bool = False,
    ) -> VariableStats:
        """Calculate statistics for a variable."""
        n_total = len(data)
        n_missing = int(data.isna().sum())
        n_valid = n_total - n_missing
        missing_pct = (n_missing / n_total * 100) if n_total > 0 else 0
        
        stats_obj = VariableStats(
            name=name,
            var_type=var_type,
            n=n_valid,
            n_missing=n_missing,
            missing_pct=missing_pct,
        )
        
        clean_data = data.dropna()
        
        if var_type == VariableType.CONTINUOUS:
            if len(clean_data) > 0:
                stats_obj.mean = float(clean_data.mean())
                stats_obj.std = float(clean_data.std())
                stats_obj.median = float(clean_data.median())
                stats_obj.q25 = float(clean_data.quantile(0.25))
                stats_obj.q75 = float(clean_data.quantile(0.75))
                stats_obj.min_val = float(clean_data.min())
                stats_obj.max_val = float(clean_data.max())
        
        elif var_type in [VariableType.CATEGORICAL, VariableType.BINARY]:
            counts = clean_data.value_counts().to_dict()
            stats_obj.categories = {str(k): int(v) for k, v in counts.items()}
            
            total = sum(counts.values())
            if total > 0:
                stats_obj.category_pcts = {
                    str(k): (v / total * 100) for k, v in counts.items()
                }
            else:
                stats_obj.category_pcts = {}
        
        return stats_obj
    
    def _calculate_pvalue(
        self,
        df: pd.DataFrame,
        column: str,
        groupby: str,
        groups: List,
        var_type: VariableType,
    ) -> Tuple[Optional[float], Optional[TestType], Optional[float]]:
        """Calculate p-value for group comparison."""
        try:
            group_data = [df[df[groupby] == g][column].dropna() for g in groups]
            
            # Check if enough data
            if any(len(d) < 2 for d in group_data):
                return None, TestType.NONE, None
            
            if var_type == VariableType.CONTINUOUS:
                # Check normality for all groups
                all_normal = True
                for gd in group_data:
                    if len(gd) >= 8:
                        try:
                            _, p = stats.shapiro(gd) if len(gd) < 5000 else stats.normaltest(gd)
                            if p < self.normality_threshold:
                                all_normal = False
                                break
                        except:
                            all_normal = False
                            break
                
                if len(groups) == 2:
                    if all_normal:
                        stat, p = stats.ttest_ind(group_data[0], group_data[1])
                        return p, TestType.TTEST, stat
                    else:
                        stat, p = stats.mannwhitneyu(group_data[0], group_data[1], alternative='two-sided')
                        return p, TestType.MANN_WHITNEY, stat
                else:
                    if all_normal:
                        stat, p = stats.f_oneway(*group_data)
                        return p, TestType.ANOVA, stat
                    else:
                        stat, p = stats.kruskal(*group_data)
                        return p, TestType.KRUSKAL_WALLIS, stat
            
            elif var_type in [VariableType.CATEGORICAL, VariableType.BINARY]:
                # Create contingency table
                contingency = pd.crosstab(df[column], df[groupby])
                
                # Check minimum expected cell count
                expected = stats.chi2_contingency(contingency)[3]
                min_expected = expected.min()
                
                if min_expected < self.min_category_count:
                    # Use Fisher's exact test (only for 2x2)
                    if contingency.shape == (2, 2):
                        stat, p = stats.fisher_exact(contingency)
                        return p, TestType.FISHER_EXACT, stat
                    else:
                        # Fall back to Chi-square with warning
                        stat, p, _, _ = stats.chi2_contingency(contingency)
                        return p, TestType.CHI_SQUARE, stat
                else:
                    stat, p, _, _ = stats.chi2_contingency(contingency)
                    return p, TestType.CHI_SQUARE, stat
        
        except Exception as e:
            logger.warning(f"Failed to calculate p-value for {column}: {e}")
            return None, TestType.NONE, None
        
        return None, TestType.NONE, None
    
    def _calculate_smd(
        self,
        df: pd.DataFrame,
        column: str,
        groupby: str,
        groups: List,
        var_type: VariableType,
    ) -> Optional[float]:
        """Calculate Standardized Mean Difference (Cohen's d)."""
        if len(groups) != 2:
            return None
        
        try:
            g1_data = df[df[groupby] == groups[0]][column].dropna()
            g2_data = df[df[groupby] == groups[1]][column].dropna()
            
            if len(g1_data) < 2 or len(g2_data) < 2:
                return None
            
            if var_type == VariableType.CONTINUOUS:
                # Cohen's d for continuous
                mean1, mean2 = g1_data.mean(), g2_data.mean()
                std1, std2 = g1_data.std(), g2_data.std()
                n1, n2 = len(g1_data), len(g2_data)
                
                # Pooled standard deviation
                pooled_std = np.sqrt(
                    ((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)
                )
                
                if pooled_std > 0:
                    return abs(mean1 - mean2) / pooled_std
            
            elif var_type in [VariableType.CATEGORICAL, VariableType.BINARY]:
                # For binary: difference in proportions / pooled SE
                # Get first category proportion
                all_cats = pd.concat([g1_data, g2_data]).unique()
                if len(all_cats) == 2:
                    cat = all_cats[0]
                    p1 = (g1_data == cat).mean()
                    p2 = (g2_data == cat).mean()
                    
                    # Pooled proportion
                    p_pooled = ((g1_data == cat).sum() + (g2_data == cat).sum()) / (len(g1_data) + len(g2_data))
                    
                    if p_pooled > 0 and p_pooled < 1:
                        # Using Cohen's h (arcsine transformation)
                        h = 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))
                        return abs(h)
        
        except Exception as e:
            logger.warning(f"Failed to calculate SMD for {column}: {e}")
        
        return None


# =============================================================================
# Formatting Functions
# =============================================================================

def _format_value(
    stats: VariableStats,
    var_type: VariableType,
    is_nonnormal: bool = False,
    show_missing: bool = True,
) -> str:
    """Format a single variable's statistics as string."""
    if var_type == VariableType.CONTINUOUS:
        if is_nonnormal:
            return f"{safe_round(stats.median, 1)} [{safe_round(stats.q25, 1)}-{safe_round(stats.q75, 1)}]"
        else:
            return f"{safe_round(stats.mean, 1)} ± {safe_round(stats.std, 1)}"
    else:
        # Return empty for categorical (categories shown separately)
        return ""


def _format_pvalue(p: Optional[float]) -> str:
    """Format p-value for display."""
    if p is None:
        return ""
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _format_as_markdown(result: TableOneResult) -> str:
    """Generate Markdown formatted Table 1."""
    lines = []
    lines.append(f"## {result.title}")
    lines.append("")
    
    # Header
    headers = ["Variable"]
    if result.overall_stats:
        headers.append(f"Overall (n={result.n_total})")
    for g in result.group_names:
        headers.append(f"{g} (n={result.group_sizes.get(g, 0)})")
    if result.show_pvalue and result.n_groups >= 2:
        headers.append("P-value")
    if result.show_smd and result.n_groups == 2:
        headers.append("SMD")
    
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    
    # Data rows
    for var in result.variables:
        is_cat = var in result.categorical_vars
        is_nonnormal = var in result.nonnormal_vars
        
        overall = result.overall_stats.get(var)
        
        if is_cat:
            # Variable name row
            row = [f"**{var}**"]
            if overall:
                row.append("")
            for g in result.group_names:
                row.append("")
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                row.append(_format_pvalue(p))
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                row.append(f"{safe_round(smd, 3)}" if smd else "")
            lines.append("| " + " | ".join(row) + " |")
            
            # Category rows
            all_cats = set()
            if overall and overall.categories:
                all_cats.update(overall.categories.keys())
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats and gstats.categories:
                    all_cats.update(gstats.categories.keys())
            
            for cat in sorted(all_cats):
                row = [f"  {cat}"]
                if overall:
                    count = overall.categories.get(cat, 0) if overall.categories else 0
                    pct = overall.category_pcts.get(cat, 0) if overall.category_pcts else 0
                    row.append(f"{count} ({safe_round(pct, 1)}%)")
                for g in result.group_names:
                    gstats = result.group_stats.get(g, {}).get(var)
                    if gstats:
                        count = gstats.categories.get(cat, 0) if gstats.categories else 0
                        pct = gstats.category_pcts.get(cat, 0) if gstats.category_pcts else 0
                        row.append(f"{count} ({safe_round(pct, 1)}%)")
                    else:
                        row.append("")
                if result.show_pvalue and result.n_groups >= 2:
                    row.append("")
                if result.show_smd and result.n_groups == 2:
                    row.append("")
                lines.append("| " + " | ".join(row) + " |")
        
        else:
            # Continuous variable
            suffix = " †" if is_nonnormal else ""
            row = [f"{var}{suffix}"]
            
            if overall:
                row.append(_format_value(overall, VariableType.CONTINUOUS, is_nonnormal))
            
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats:
                    row.append(_format_value(gstats, VariableType.CONTINUOUS, is_nonnormal))
                else:
                    row.append("")
            
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                row.append(_format_pvalue(p))
            
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                row.append(f"{safe_round(smd, 3)}" if smd else "")
            
            lines.append("| " + " | ".join(row) + " |")
    
    # Footer notes
    lines.append("")
    if result.nonnormal_vars:
        lines.append("† Median [IQR]; other continuous variables as Mean ± SD")
    lines.append("Categorical variables as n (%)")
    
    return "\n".join(lines)


def _format_as_html(result: TableOneResult) -> str:
    """Generate HTML formatted Table 1."""
    lines = []
    lines.append(f'<table class="tableone">')
    lines.append(f'<caption>{result.title}</caption>')
    lines.append('<thead><tr>')
    
    # Header
    lines.append('<th>Variable</th>')
    if result.overall_stats:
        lines.append(f'<th>Overall (n={result.n_total})</th>')
    for g in result.group_names:
        lines.append(f'<th>{g} (n={result.group_sizes.get(g, 0)})</th>')
    if result.show_pvalue and result.n_groups >= 2:
        lines.append('<th>P-value</th>')
    if result.show_smd and result.n_groups == 2:
        lines.append('<th>SMD</th>')
    
    lines.append('</tr></thead>')
    lines.append('<tbody>')
    
    # Data rows
    for var in result.variables:
        is_cat = var in result.categorical_vars
        is_nonnormal = var in result.nonnormal_vars
        overall = result.overall_stats.get(var)
        
        if is_cat:
            lines.append('<tr>')
            lines.append(f'<td><strong>{var}</strong></td>')
            if overall:
                lines.append('<td></td>')
            for g in result.group_names:
                lines.append('<td></td>')
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                lines.append(f'<td>{_format_pvalue(p)}</td>')
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                lines.append(f'<td>{safe_round(smd, 3) if smd else ""}</td>')
            lines.append('</tr>')
            
            # Categories
            all_cats = set()
            if overall and overall.categories:
                all_cats.update(overall.categories.keys())
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats and gstats.categories:
                    all_cats.update(gstats.categories.keys())
            
            for cat in sorted(all_cats):
                lines.append('<tr>')
                lines.append(f'<td style="padding-left:20px">{cat}</td>')
                if overall:
                    count = overall.categories.get(cat, 0) if overall.categories else 0
                    pct = overall.category_pcts.get(cat, 0) if overall.category_pcts else 0
                    lines.append(f'<td>{count} ({safe_round(pct, 1)}%)</td>')
                for g in result.group_names:
                    gstats = result.group_stats.get(g, {}).get(var)
                    if gstats:
                        count = gstats.categories.get(cat, 0) if gstats.categories else 0
                        pct = gstats.category_pcts.get(cat, 0) if gstats.category_pcts else 0
                        lines.append(f'<td>{count} ({safe_round(pct, 1)}%)</td>')
                    else:
                        lines.append('<td></td>')
                if result.show_pvalue and result.n_groups >= 2:
                    lines.append('<td></td>')
                if result.show_smd and result.n_groups == 2:
                    lines.append('<td></td>')
                lines.append('</tr>')
        
        else:
            lines.append('<tr>')
            suffix = " †" if is_nonnormal else ""
            lines.append(f'<td>{var}{suffix}</td>')
            
            if overall:
                lines.append(f'<td>{_format_value(overall, VariableType.CONTINUOUS, is_nonnormal)}</td>')
            
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats:
                    lines.append(f'<td>{_format_value(gstats, VariableType.CONTINUOUS, is_nonnormal)}</td>')
                else:
                    lines.append('<td></td>')
            
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                lines.append(f'<td>{_format_pvalue(p)}</td>')
            
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                lines.append(f'<td>{safe_round(smd, 3) if smd else ""}</td>')
            
            lines.append('</tr>')
    
    lines.append('</tbody>')
    lines.append('<tfoot><tr>')
    colspan = 1 + (1 if result.overall_stats else 0) + len(result.group_names) + \
              (1 if result.show_pvalue and result.n_groups >= 2 else 0) + \
              (1 if result.show_smd and result.n_groups == 2 else 0)
    
    footnotes = []
    if result.nonnormal_vars:
        footnotes.append("† Median [IQR]; other continuous variables as Mean ± SD")
    footnotes.append("Categorical variables as n (%)")
    
    lines.append(f'<td colspan="{colspan}">{"; ".join(footnotes)}</td>')
    lines.append('</tr></tfoot>')
    lines.append('</table>')
    
    return "\n".join(lines)


def _format_as_latex(result: TableOneResult) -> str:
    """Generate LaTeX formatted Table 1."""
    lines = []
    
    # Column count
    n_cols = 1 + (1 if result.overall_stats else 0) + len(result.group_names) + \
             (1 if result.show_pvalue and result.n_groups >= 2 else 0) + \
             (1 if result.show_smd and result.n_groups == 2 else 0)
    
    col_spec = "l" + "c" * (n_cols - 1)
    
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(f"\\caption{{{result.title}}}")
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    
    # Header
    header_parts = ["Variable"]
    if result.overall_stats:
        header_parts.append(f"Overall (n={result.n_total})")
    for g in result.group_names:
        header_parts.append(f"{g} (n={result.group_sizes.get(g, 0)})")
    if result.show_pvalue and result.n_groups >= 2:
        header_parts.append("P-value")
    if result.show_smd and result.n_groups == 2:
        header_parts.append("SMD")
    
    lines.append(" & ".join(header_parts) + r" \\")
    lines.append(r"\hline")
    
    # Data rows
    for var in result.variables:
        is_cat = var in result.categorical_vars
        is_nonnormal = var in result.nonnormal_vars
        overall = result.overall_stats.get(var)
        
        if is_cat:
            row = [f"\\textbf{{{var}}}"]
            if overall:
                row.append("")
            for g in result.group_names:
                row.append("")
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                row.append(_format_pvalue(p))
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                row.append(f"{safe_round(smd, 3)}" if smd else "")
            lines.append(" & ".join(row) + r" \\")
            
            all_cats = set()
            if overall and overall.categories:
                all_cats.update(overall.categories.keys())
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats and gstats.categories:
                    all_cats.update(gstats.categories.keys())
            
            for cat in sorted(all_cats):
                row = [f"\\quad {cat}"]
                if overall:
                    count = overall.categories.get(cat, 0) if overall.categories else 0
                    pct = overall.category_pcts.get(cat, 0) if overall.category_pcts else 0
                    row.append(f"{count} ({safe_round(pct, 1)}\\%)")
                for g in result.group_names:
                    gstats = result.group_stats.get(g, {}).get(var)
                    if gstats:
                        count = gstats.categories.get(cat, 0) if gstats.categories else 0
                        pct = gstats.category_pcts.get(cat, 0) if gstats.category_pcts else 0
                        row.append(f"{count} ({safe_round(pct, 1)}\\%)")
                    else:
                        row.append("")
                if result.show_pvalue and result.n_groups >= 2:
                    row.append("")
                if result.show_smd and result.n_groups == 2:
                    row.append("")
                lines.append(" & ".join(row) + r" \\")
        
        else:
            suffix = "$^\\dagger$" if is_nonnormal else ""
            row = [f"{var}{suffix}"]
            
            if overall:
                val = _format_value(overall, VariableType.CONTINUOUS, is_nonnormal)
                row.append(val.replace("±", r"$\pm$"))
            
            for g in result.group_names:
                gstats = result.group_stats.get(g, {}).get(var)
                if gstats:
                    val = _format_value(gstats, VariableType.CONTINUOUS, is_nonnormal)
                    row.append(val.replace("±", r"$\pm$"))
                else:
                    row.append("")
            
            if result.show_pvalue and result.n_groups >= 2:
                p = overall.p_value if overall else None
                row.append(_format_pvalue(p))
            
            if result.show_smd and result.n_groups == 2:
                smd = overall.smd if overall else None
                row.append(f"{safe_round(smd, 3)}" if smd else "")
            
            lines.append(" & ".join(row) + r" \\")
    
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    
    # Footnotes
    footnotes = []
    if result.nonnormal_vars:
        footnotes.append(r"$^\dagger$ Median [IQR]; other continuous variables as Mean $\pm$ SD")
    footnotes.append("Categorical variables as n (\\%)")
    
    lines.append(f"\\par\\small {'; '.join(footnotes)}")
    lines.append(r"\end{table}")
    
    return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def generate_tableone(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    categorical: Optional[List[str]] = None,
    nonnormal: Optional[List[str]] = None,
    groupby: Optional[str] = None,
    pval: bool = True,
    smd: bool = False,
    missing: bool = True,
    output_format: Literal["dict", "markdown", "html", "latex"] = "dict",
    title: str = "Table 1. Baseline Characteristics",
) -> Any:
    """
    Generate Table 1 (baseline characteristics table).
    
    This is a convenience function that creates a TableOneGenerator
    and generates the table in one call.
    
    Args:
        df: Input DataFrame
        columns: Columns to include (default: all)
        categorical: Columns to treat as categorical
        nonnormal: Continuous columns to report as median [IQR]
        groupby: Column for stratification (e.g., "treatment_group")
        pval: Include p-values for group comparisons
        smd: Include standardized mean difference
        missing: Include missing value counts
        output_format: "dict", "markdown", "html", or "latex"
        title: Table title
    
    Returns:
        Table 1 in requested format
    
    Example:
        # Generate Table 1 as Markdown
        table = generate_tableone(
            df=patient_data,
            groupby="treatment",
            categorical=["gender", "smoking_status"],
            nonnormal=["age"],
            pval=True,
            output_format="markdown"
        )
        print(table)
    """
    generator = TableOneGenerator()
    result = generator.generate(
        df=df,
        columns=columns,
        categorical=categorical,
        nonnormal=nonnormal,
        groupby=groupby,
        pval=pval,
        smd=smd,
        missing=missing,
        title=title,
    )
    
    if output_format == "dict":
        return result.to_dict()
    elif output_format == "markdown":
        return result.to_markdown()
    elif output_format == "html":
        return result.to_html()
    elif output_format == "latex":
        return result.to_latex()
    else:
        return result.to_dict()


def quick_tableone(
    df: pd.DataFrame,
    groupby: Optional[str] = None,
    pval: bool = True,
) -> str:
    """
    Quick Table 1 generation with automatic variable detection.
    
    Returns Markdown format by default.
    """
    return generate_tableone(
        df=df,
        groupby=groupby,
        pval=pval,
        output_format="markdown",
    )

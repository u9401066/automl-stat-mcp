"""
Auto Analyze Task - Intelligent Statistical Analysis Engine

Automatically performs comprehensive statistical analysis based on data characteristics.
No manual method selection required - the engine decides what's appropriate.
"""
import logging
import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


@dataclass
class ColumnProfile:
    """Profile for a single column"""
    name: str
    dtype: str
    inferred_type: str  # numeric, categorical, datetime, id, constant
    n_unique: int
    n_missing: int
    missing_pct: float
    is_analyzable: bool = True

    # Numeric stats (if applicable)
    mean: Optional[float] = None
    std: Optional[float] = None
    median: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    is_normal: Optional[bool] = None
    normality_pvalue: Optional[float] = None
    n_outliers_iqr: Optional[int] = None
    n_outliers_zscore: Optional[int] = None

    # Categorical stats (if applicable)
    mode: Optional[str] = None
    mode_freq: Optional[int] = None
    top_values: Optional[List[Dict]] = None


@dataclass
class AssociationResult:
    """Result of association analysis between two variables"""
    var1: str
    var2: str
    test_name: str
    statistic: float
    pvalue: float
    effect_size: Optional[float] = None
    effect_size_name: Optional[str] = None
    interpretation: Optional[str] = None


@dataclass
class AutoAnalyzeResult:
    """Complete auto-analysis result"""
    # Metadata
    n_rows: int
    n_cols: int
    n_duplicates: int
    memory_usage_mb: float

    # Column profiles
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)

    # Grouped column lists
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)
    id_columns: List[str] = field(default_factory=list)
    constant_columns: List[str] = field(default_factory=list)

    # Data quality
    quality_score: float = 0.0
    quality_issues: List[str] = field(default_factory=list)

    # Association analysis (with target)
    target_column: Optional[str] = None
    associations: List[AssociationResult] = field(default_factory=list)

    # Correlation matrix (numeric only)
    correlation_matrix: Optional[Dict] = None

    # Recommendations
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "metadata": {
                "n_rows": self.n_rows,
                "n_cols": self.n_cols,
                "n_duplicates": self.n_duplicates,
                "memory_usage_mb": safe_round(self.memory_usage_mb, 2),
            },
            "column_summary": {
                "numeric": self.numeric_columns,
                "categorical": self.categorical_columns,
                "datetime": self.datetime_columns,
                "id_columns": self.id_columns,
                "constant": self.constant_columns,
            },
            "columns": {
                name: self._profile_to_dict(profile)
                for name, profile in self.columns.items()
            },
            "data_quality": {
                "score": safe_round(self.quality_score, 2),
                "issues": self.quality_issues,
            },
            "target_analysis": {
                "target_column": self.target_column,
                "associations": [
                    {
                        "variable": a.var1,
                        "test": a.test_name,
                        "statistic": safe_round(a.statistic, 4),
                        "p_value": safe_round(a.pvalue, 4),
                        "effect_size": safe_round(a.effect_size, 4),
                        "effect_size_name": a.effect_size_name,
                        "interpretation": a.interpretation,
                    }
                    for a in self.associations
                ],
            } if self.target_column else None,
            "correlation_matrix": self.correlation_matrix,
            "recommendations": self.recommendations,
        }

    def _profile_to_dict(self, p: ColumnProfile) -> Dict:
        """Convert column profile to dict"""
        base = {
            "dtype": p.dtype,
            "inferred_type": p.inferred_type,
            "n_unique": p.n_unique,
            "n_missing": p.n_missing,
            "missing_pct": safe_round(p.missing_pct, 2),
        }

        if p.inferred_type == "numeric":
            base.update({
                "mean": safe_round(p.mean, 4),
                "std": safe_round(p.std, 4),
                "median": safe_round(p.median, 4),
                "min": safe_round(p.min_val, 4),
                "max": safe_round(p.max_val, 4),
                "q25": safe_round(p.q25, 4),
                "q75": safe_round(p.q75, 4),
                "skewness": safe_round(p.skewness, 4),
                "kurtosis": safe_round(p.kurtosis, 4),
                "is_normal": p.is_normal,
                "normality_pvalue": safe_round(p.normality_pvalue, 4),
                "n_outliers_iqr": p.n_outliers_iqr,
                "n_outliers_zscore": p.n_outliers_zscore,
            })
        elif p.inferred_type == "categorical":
            base.update({
                "mode": p.mode,
                "mode_freq": p.mode_freq,
                "top_values": p.top_values,
            })

        return base


class AutoAnalyzeEngine:
    """
    Intelligent Statistical Analysis Engine

    Automatically determines appropriate statistical methods based on:
    - Variable types (numeric, categorical, datetime)
    - Distribution characteristics (normal vs non-normal)
    - Number of groups (for categorical)
    - Sample size
    """

    def __init__(self, df: pd.DataFrame, target_column: Optional[str] = None):
        self.df = df
        self.target_column = target_column
        self.result = AutoAnalyzeResult(
            n_rows=len(df),
            n_cols=len(df.columns),
            n_duplicates=df.duplicated().sum(),
            memory_usage_mb=df.memory_usage(deep=True).sum() / 1024 / 1024,
            target_column=target_column,
        )

    def analyze(self) -> AutoAnalyzeResult:
        """Run complete auto-analysis"""
        logger.info(f"Starting auto-analysis: {self.result.n_rows} rows, {self.result.n_cols} columns")

        # Step 1: Profile all columns
        self._profile_columns()

        # Step 2: Calculate data quality score
        self._calculate_quality_score()

        # Step 3: Correlation matrix for numeric columns
        if len(self.result.numeric_columns) >= 2:
            self._compute_correlation_matrix()

        # Step 4: Target association analysis
        if self.target_column and self.target_column in self.df.columns:
            self._analyze_target_associations()

        # Step 5: Generate recommendations
        self._generate_recommendations()

        logger.info("Auto-analysis completed")
        return self.result

    def _profile_columns(self):
        """Profile each column and infer types"""
        for col in self.df.columns:
            profile = self._profile_single_column(col)
            self.result.columns[col] = profile

            # Categorize column
            if profile.inferred_type == "numeric":
                self.result.numeric_columns.append(col)
            elif profile.inferred_type == "categorical":
                self.result.categorical_columns.append(col)
            elif profile.inferred_type == "datetime":
                self.result.datetime_columns.append(col)
            elif profile.inferred_type == "id":
                self.result.id_columns.append(col)
            elif profile.inferred_type == "constant":
                self.result.constant_columns.append(col)

    def _profile_single_column(self, col: str) -> ColumnProfile:
        """Profile a single column"""
        series = self.df[col]

        n_unique = series.nunique()
        n_missing = series.isna().sum()
        missing_pct = (n_missing / len(series)) * 100

        # Infer type
        inferred_type = self._infer_column_type(series, col, n_unique)

        profile = ColumnProfile(
            name=col,
            dtype=str(series.dtype),
            inferred_type=inferred_type,
            n_unique=n_unique,
            n_missing=n_missing,
            missing_pct=missing_pct,
        )

        # Add type-specific stats
        if inferred_type == "numeric":
            self._add_numeric_stats(profile, series)
        elif inferred_type == "categorical":
            self._add_categorical_stats(profile, series)

        return profile

    def _infer_column_type(self, series: pd.Series, col_name: str, n_unique: int) -> str:
        """Infer the semantic type of a column"""
        # Check for constant
        if n_unique <= 1:
            return "constant"

        # Check for ID-like columns
        col_lower = col_name.lower()
        if any(id_hint in col_lower for id_hint in ['id', 'index', 'key', 'code', 'uuid']):
            if n_unique == len(self.df) or n_unique > len(self.df) * 0.95:
                return "id"

        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # Try to infer datetime from string
        if series.dtype == 'object':
            try:
                sample = series.dropna().head(100)
                pd.to_datetime(sample, infer_datetime_format=True)
                if len(sample) > 10:
                    return "datetime"
            except Exception:
                pass

        # Numeric
        if pd.api.types.is_numeric_dtype(series):
            # Check if it's actually categorical (few unique values)
            if n_unique <= 10 and n_unique < len(self.df) * 0.05:
                return "categorical"
            return "numeric"

        # Default to categorical for object types
        return "categorical"

    def _add_numeric_stats(self, profile: ColumnProfile, series: pd.Series):
        """Add numeric statistics to profile"""
        clean = series.dropna()

        if len(clean) == 0:
            profile.is_analyzable = False
            return

        # Basic stats
        profile.mean = float(clean.mean())
        profile.std = float(clean.std())
        profile.median = float(clean.median())
        profile.min_val = float(clean.min())
        profile.max_val = float(clean.max())
        profile.q25 = float(clean.quantile(0.25))
        profile.q75 = float(clean.quantile(0.75))

        # Shape stats
        profile.skewness = float(clean.skew())
        profile.kurtosis = float(clean.kurtosis())

        # Normality test (Shapiro-Wilk for small samples, D'Agostino for large)
        try:
            if len(clean) < 5000:
                sample = clean.sample(min(len(clean), 5000))
                _, pvalue = stats.shapiro(sample)
            else:
                _, pvalue = stats.normaltest(clean)

            profile.is_normal = pvalue > 0.05
            profile.normality_pvalue = float(pvalue)
        except Exception:
            profile.is_normal = None
            profile.normality_pvalue = None

        # Outlier detection - IQR method
        iqr = profile.q75 - profile.q25
        lower_bound = profile.q25 - 1.5 * iqr
        upper_bound = profile.q75 + 1.5 * iqr
        profile.n_outliers_iqr = int(((clean < lower_bound) | (clean > upper_bound)).sum())

        # Outlier detection - Z-score method
        z_scores = np.abs((clean - profile.mean) / profile.std) if profile.std > 0 else pd.Series([0] * len(clean))
        profile.n_outliers_zscore = int((z_scores > 3).sum())

    def _add_categorical_stats(self, profile: ColumnProfile, series: pd.Series):
        """Add categorical statistics to profile"""
        value_counts = series.value_counts()

        if len(value_counts) > 0:
            profile.mode = str(value_counts.index[0])
            profile.mode_freq = int(value_counts.iloc[0])

            # Top values
            top_n = min(10, len(value_counts))
            profile.top_values = [
                {"value": str(val), "count": int(cnt), "pct": safe_round(cnt / len(series) * 100, 2)}
                for val, cnt in value_counts.head(top_n).items()
            ]

    def _calculate_quality_score(self):
        """Calculate overall data quality score (0-100)"""
        issues = []
        score = 100.0

        # Check missing values
        total_missing = sum(p.n_missing for p in self.result.columns.values())
        total_cells = self.result.n_rows * self.result.n_cols
        missing_pct = (total_missing / total_cells) * 100 if total_cells > 0 else 0

        if missing_pct > 50:
            score -= 30
            issues.append(f"High missing rate: {missing_pct:.1f}% of data is missing")
        elif missing_pct > 20:
            score -= 15
            issues.append(f"Moderate missing rate: {missing_pct:.1f}% of data is missing")
        elif missing_pct > 5:
            score -= 5
            issues.append(f"Some missing values: {missing_pct:.1f}% of data is missing")

        # Check duplicates
        dup_pct = (self.result.n_duplicates / self.result.n_rows) * 100 if self.result.n_rows > 0 else 0
        if dup_pct > 20:
            score -= 15
            issues.append(f"High duplicate rate: {dup_pct:.1f}% duplicate rows")
        elif dup_pct > 5:
            score -= 5
            issues.append(f"Some duplicates: {dup_pct:.1f}% duplicate rows")

        # Check constant columns
        if self.result.constant_columns:
            score -= 5 * len(self.result.constant_columns)
            issues.append(f"Constant columns (no variance): {', '.join(self.result.constant_columns)}")

        # Check for columns with high missing
        high_missing_cols = [
            name for name, p in self.result.columns.items()
            if p.missing_pct > 50
        ]
        if high_missing_cols:
            issues.append(f"Columns with >50% missing: {', '.join(high_missing_cols)}")

        # Check for outliers
        high_outlier_cols = [
            name for name, p in self.result.columns.items()
            if p.inferred_type == "numeric" and p.n_outliers_iqr and p.n_outliers_iqr > self.result.n_rows * 0.1
        ]
        if high_outlier_cols:
            score -= 5
            issues.append(f"Columns with many outliers (>10%): {', '.join(high_outlier_cols)}")

        self.result.quality_score = max(0, score)
        self.result.quality_issues = issues

    def _compute_correlation_matrix(self):
        """Compute correlation matrix for numeric columns"""
        numeric_df = self.df[self.result.numeric_columns].dropna()

        if len(numeric_df) < 5:
            return

        # Pearson correlation
        corr_matrix = numeric_df.corr()

        # Clean NaN/Inf values in correlation matrix
        corr_dict = {}
        for col in corr_matrix.columns:
            corr_dict[col] = {
                k: safe_round(v, 4) for k, v in corr_matrix[col].to_dict().items()
            }

        self.result.correlation_matrix = {
            "columns": self.result.numeric_columns,
            "values": corr_dict,
            "high_correlations": self._find_high_correlations(corr_matrix)
        }

    def _find_high_correlations(self, corr_matrix: pd.DataFrame, threshold: float = 0.7) -> List[Dict]:
        """Find highly correlated pairs"""
        high_corr = []
        cols = corr_matrix.columns.tolist()

        for i, col1 in enumerate(cols):
            for col2 in cols[i+1:]:
                corr = corr_matrix.loc[col1, col2]
                if pd.notna(corr) and abs(corr) >= threshold:
                    high_corr.append({
                        "var1": col1,
                        "var2": col2,
                        "correlation": safe_round(corr, 4),
                        "strength": "strong" if abs(corr) >= 0.8 else "moderate"
                    })

        return sorted(high_corr, key=lambda x: abs(x["correlation"] or 0), reverse=True)

    def _analyze_target_associations(self):
        """Analyze associations between features and target"""
        if not self.target_column:
            return

        target_col = self.target_column
        target_profile = self.result.columns.get(target_col)

        if not target_profile:
            return

        target_is_numeric = target_profile.inferred_type == "numeric"

        for col in self.df.columns:
            if col == target_col:
                continue

            col_profile = self.result.columns.get(col)
            if not col_profile or not col_profile.is_analyzable:
                continue

            if col_profile.inferred_type in ["id", "constant", "datetime"]:
                continue

            col_is_numeric = col_profile.inferred_type == "numeric"

            # Choose appropriate test
            association = self._compute_association(
                col, target_col,
                col_is_numeric, target_is_numeric,
                col_profile, target_profile
            )

            if association:
                self.result.associations.append(association)

        # Sort by p-value
        self.result.associations.sort(key=lambda x: x.pvalue)

    def _compute_association(
        self,
        col1: str,
        col2: str,
        col1_numeric: bool,
        col2_numeric: bool,
        profile1: ColumnProfile,
        profile2: ColumnProfile
    ) -> Optional[AssociationResult]:
        """Compute appropriate association test"""
        try:
            data = self.df[[col1, col2]].dropna()

            if len(data) < 5:
                return None

            x = data[col1]
            y = data[col2]

            # Numeric vs Numeric: Correlation
            if col1_numeric and col2_numeric:
                # Use Spearman if either is non-normal
                if not profile1.is_normal or not profile2.is_normal:
                    corr, pval = stats.spearmanr(x, y)
                    test_name = "Spearman correlation"
                else:
                    corr, pval = stats.pearsonr(x, y)
                    test_name = "Pearson correlation"

                return AssociationResult(
                    var1=col1, var2=col2,
                    test_name=test_name,
                    statistic=corr,
                    pvalue=pval,
                    effect_size=abs(corr),
                    effect_size_name="r",
                    interpretation=self._interpret_correlation(corr, pval)
                )

            # Categorical vs Categorical: Chi-square
            elif not col1_numeric and not col2_numeric:
                contingency = pd.crosstab(x, y)
                chi2, pval, dof, expected = stats.chi2_contingency(contingency)

                # Cramér's V
                n = contingency.sum().sum()
                min_dim = min(contingency.shape) - 1
                cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0

                return AssociationResult(
                    var1=col1, var2=col2,
                    test_name="Chi-square test",
                    statistic=chi2,
                    pvalue=pval,
                    effect_size=cramers_v,
                    effect_size_name="Cramér's V",
                    interpretation=self._interpret_cramers_v(cramers_v, pval)
                )

            # Numeric vs Categorical (or vice versa)
            else:
                numeric_col = col1 if col1_numeric else col2
                cat_col = col2 if col1_numeric else col1
                numeric_profile = profile1 if col1_numeric else profile2

                groups = self.df.groupby(cat_col)[numeric_col].apply(list).to_dict()
                group_data = [v for v in groups.values() if len(v) >= 2]

                if len(group_data) < 2:
                    return None

                n_groups = len(group_data)

                # Two groups: t-test or Mann-Whitney
                if n_groups == 2:
                    g1, g2 = group_data[0], group_data[1]

                    # Check if parametric is appropriate
                    if numeric_profile.is_normal:
                        stat, pval = stats.ttest_ind(g1, g2)
                        test_name = "Independent t-test"
                        # Cohen's d
                        pooled_std = np.sqrt(((len(g1)-1)*np.var(g1) + (len(g2)-1)*np.var(g2)) / (len(g1)+len(g2)-2))
                        effect = abs(np.mean(g1) - np.mean(g2)) / pooled_std if pooled_std > 0 else 0
                        effect_name = "Cohen's d"
                    else:
                        stat, pval = stats.mannwhitneyu(g1, g2, alternative='two-sided')
                        test_name = "Mann-Whitney U"
                        # Rank-biserial correlation
                        n1, n2 = len(g1), len(g2)
                        effect = 1 - (2*stat)/(n1*n2)
                        effect_name = "rank-biserial r"

                # More than two groups: ANOVA or Kruskal-Wallis
                else:
                    if numeric_profile.is_normal:
                        stat, pval = stats.f_oneway(*group_data)
                        test_name = "One-way ANOVA"
                        # Eta-squared (approximate)
                        total_mean = np.mean([x for g in group_data for x in g])
                        ss_between = sum(len(g) * (np.mean(g) - total_mean)**2 for g in group_data)
                        ss_total = sum((x - total_mean)**2 for g in group_data for x in g)
                        effect = ss_between / ss_total if ss_total > 0 else 0
                        effect_name = "η²"
                    else:
                        stat, pval = stats.kruskal(*group_data)
                        test_name = "Kruskal-Wallis H"
                        # Epsilon-squared
                        n = sum(len(g) for g in group_data)
                        effect = (stat - n_groups + 1) / (n - n_groups) if n > n_groups else 0
                        effect_name = "ε²"

                return AssociationResult(
                    var1=col1, var2=col2,
                    test_name=test_name,
                    statistic=stat,
                    pvalue=pval,
                    effect_size=effect,
                    effect_size_name=effect_name,
                    interpretation=self._interpret_effect_size(effect, effect_name, pval)
                )

        except Exception as e:
            logger.warning(f"Failed to compute association for {col1} vs {col2}: {e}")
            return None

    def _interpret_correlation(self, r: float, pval: float) -> str:
        """Interpret correlation coefficient"""
        if pval > 0.05:
            return "No significant correlation"

        abs_r = abs(r)
        direction = "positive" if r > 0 else "negative"

        if abs_r >= 0.8:
            strength = "Very strong"
        elif abs_r >= 0.6:
            strength = "Strong"
        elif abs_r >= 0.4:
            strength = "Moderate"
        elif abs_r >= 0.2:
            strength = "Weak"
        else:
            strength = "Very weak"

        return f"{strength} {direction} correlation (r={r:.3f}, p={pval:.4f})"

    def _interpret_cramers_v(self, v: float, pval: float) -> str:
        """Interpret Cramér's V"""
        if pval > 0.05:
            return "No significant association"

        if v >= 0.5:
            strength = "Strong"
        elif v >= 0.3:
            strength = "Moderate"
        elif v >= 0.1:
            strength = "Weak"
        else:
            strength = "Very weak"

        return f"{strength} association (V={v:.3f}, p={pval:.4f})"

    def _interpret_effect_size(self, effect: float, name: str, pval: float) -> str:
        """Interpret effect size"""
        if pval > 0.05:
            return f"No significant difference (p={pval:.4f})"

        if name == "Cohen's d":
            if effect >= 0.8:
                strength = "Large"
            elif effect >= 0.5:
                strength = "Medium"
            else:
                strength = "Small"
        elif name in ["η²", "ε²"]:
            if effect >= 0.14:
                strength = "Large"
            elif effect >= 0.06:
                strength = "Medium"
            else:
                strength = "Small"
        else:
            if abs(effect) >= 0.5:
                strength = "Large"
            elif abs(effect) >= 0.3:
                strength = "Medium"
            else:
                strength = "Small"

        return f"{strength} effect ({name}={effect:.3f}, p={pval:.4f})"

    def _generate_recommendations(self):
        """Generate actionable recommendations"""
        recs = []

        # Missing value recommendations
        high_missing = [
            (name, p.missing_pct) for name, p in self.result.columns.items()
            if p.missing_pct > 20
        ]
        if high_missing:
            cols_str = ", ".join([f"{n} ({p:.1f}%)" for n, p in high_missing[:5]])
            recs.append({
                "category": "data_cleaning",
                "priority": "high",
                "issue": "High missing values",
                "columns": [n for n, _ in high_missing],
                "suggestion": f"Consider imputation or removal for columns with high missing: {cols_str}"
            })

        # Outlier recommendations
        high_outliers = [
            (name, p.n_outliers_iqr) for name, p in self.result.columns.items()
            if p.n_outliers_iqr and p.n_outliers_iqr > self.result.n_rows * 0.05
        ]
        if high_outliers:
            recs.append({
                "category": "data_cleaning",
                "priority": "medium",
                "issue": "Significant outliers detected",
                "columns": [n for n, _ in high_outliers],
                "suggestion": "Review outliers - consider winsorization, transformation, or removal if appropriate"
            })

        # Skewed distributions
        skewed_cols = [
            (name, p.skewness) for name, p in self.result.columns.items()
            if p.skewness and abs(p.skewness) > 1.5
        ]
        if skewed_cols:
            recs.append({
                "category": "feature_engineering",
                "priority": "medium",
                "issue": "Highly skewed distributions",
                "columns": [n for n, _ in skewed_cols],
                "suggestion": "Consider log or Box-Cox transformation for skewed numeric features"
            })

        # High correlation (potential multicollinearity)
        if self.result.correlation_matrix and self.result.correlation_matrix.get("high_correlations"):
            high_corr = self.result.correlation_matrix["high_correlations"]
            if high_corr:
                pairs = [f"{h['var1']}-{h['var2']}" for h in high_corr[:3]]
                recs.append({
                    "category": "feature_engineering",
                    "priority": "medium",
                    "issue": "High correlations between features",
                    "details": high_corr[:5],
                    "suggestion": f"Consider removing or combining highly correlated features: {', '.join(pairs)}"
                })

        # Constant columns
        if self.result.constant_columns:
            recs.append({
                "category": "data_cleaning",
                "priority": "high",
                "issue": "Constant columns (no variance)",
                "columns": self.result.constant_columns,
                "suggestion": f"Remove constant columns: {', '.join(self.result.constant_columns)}"
            })

        # ID columns
        if self.result.id_columns:
            recs.append({
                "category": "data_cleaning",
                "priority": "high",
                "issue": "ID-like columns detected",
                "columns": self.result.id_columns,
                "suggestion": f"Exclude ID columns from modeling: {', '.join(self.result.id_columns)}"
            })

        # ML model recommendations based on target
        if self.target_column:
            target_profile = self.result.columns.get(self.target_column)
            if target_profile:
                if target_profile.inferred_type == "numeric":
                    recs.append({
                        "category": "modeling",
                        "priority": "info",
                        "issue": "Target is continuous",
                        "suggestion": "This is a regression problem. Recommended: LightGBM, XGBoost, or Neural Network"
                    })
                elif target_profile.inferred_type == "categorical":
                    n_classes = target_profile.n_unique
                    if n_classes == 2:
                        recs.append({
                            "category": "modeling",
                            "priority": "info",
                            "issue": "Binary classification target",
                            "suggestion": "This is a binary classification problem. Recommended: LightGBM, XGBoost, or Logistic Regression"
                        })
                    else:
                        recs.append({
                            "category": "modeling",
                            "priority": "info",
                            "issue": f"Multi-class classification target ({n_classes} classes)",
                            "suggestion": "This is a multi-class classification problem. Recommended: LightGBM, XGBoost, or Neural Network"
                        })

        # Sample size warning
        if self.result.n_rows < 100:
            recs.append({
                "category": "data_quality",
                "priority": "high",
                "issue": "Small sample size",
                "suggestion": f"Only {self.result.n_rows} rows. Results may not be reliable. Consider collecting more data."
            })

        self.result.recommendations = recs


def run_auto_analyze(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
    include_advanced: bool = True,
) -> Dict:
    """
    Main entry point for auto-analysis

    Args:
        df: DataFrame to analyze
        target_column: Optional target column for association analysis
        include_advanced: Include advanced analysis (VIF, missing pattern)

    Returns:
        Complete analysis result as dictionary
    """
    engine = AutoAnalyzeEngine(df, target_column)
    result = engine.analyze()
    output = result.to_dict()

    # Add advanced analysis if requested
    if include_advanced:
        try:
            from .advanced_analysis import run_enhanced_analysis
            advanced = run_enhanced_analysis(
                df,
                target_column=target_column,
                include_vif=True,
                include_missing_analysis=True,
            )
            output["advanced_analysis"] = advanced
        except ImportError:
            logger.warning("Advanced analysis module not available")
        except Exception as e:
            logger.warning(f"Advanced analysis failed: {e}")

    return output

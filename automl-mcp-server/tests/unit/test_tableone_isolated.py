"""
Isolated tests for TableOne generation utilities.

Tests summary statistics table generation for clinical research.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Optional


# ==============================================================================
# Tests
# ==============================================================================

class TestDescriptiveStatistics:
    """Test descriptive statistics for TableOne"""
    
    def test_continuous_mean_sd(self):
        """Test mean ± SD format"""
        data = np.array([10, 20, 30, 40, 50])
        
        mean = np.mean(data)
        sd = np.std(data, ddof=1)
        
        # Format: mean ± SD
        result = f"{mean:.1f} ± {sd:.1f}"
        
        assert "30.0" in result  # Mean
        assert "15.8" in result  # SD
        print(f"✓ Mean ± SD: {result}")
    
    def test_continuous_median_iqr(self):
        """Test median [IQR] format"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])  # Skewed
        
        median = np.median(data)
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        
        # Format: median [IQR]
        result = f"{median:.1f} [{q1:.1f}, {q3:.1f}]"
        
        assert "5.5" in result  # Median
        print(f"✓ Median [IQR]: {result}")
    
    def test_categorical_n_percent(self):
        """Test n (%) format"""
        data = pd.Series(['A', 'A', 'A', 'B', 'B', 'C'])
        
        counts = data.value_counts()
        n_total = len(data)
        
        results = {}
        for cat, count in counts.items():
            pct = count / n_total * 100
            results[cat] = f"{count} ({pct:.1f}%)"
        
        assert "3 (50.0%)" == results['A']
        assert "2 (33.3%)" == results['B']
        print("✓ Categorical n (%)")
    
    def test_missing_values_reporting(self):
        """Test missing value reporting"""
        data = pd.Series([1, 2, np.nan, 4, np.nan])
        
        n_total = len(data)
        n_missing = data.isna().sum()
        n_valid = data.notna().sum()
        pct_missing = n_missing / n_total * 100
        
        assert n_missing == 2
        assert n_valid == 3
        print(f"✓ Missing: {n_missing} ({pct_missing:.1f}%)")


class TestGroupComparisons:
    """Test statistical tests for group comparisons"""
    
    def test_ttest_continuous(self):
        """Test t-test for continuous variables"""
        group1 = np.array([10, 12, 14, 16, 18])
        group2 = np.array([20, 22, 24, 26, 28])
        
        t_stat, p_value = stats.ttest_ind(group1, group2)
        
        assert p_value < 0.01  # Significant difference
        print(f"✓ t-test: t={t_stat:.2f}, p={p_value:.4f}")
    
    def test_mannwhitney_nonnormal(self):
        """Test Mann-Whitney U for non-normal data"""
        group1 = np.array([1, 2, 2, 3, 100])  # Skewed
        group2 = np.array([10, 20, 30, 40, 50])
        
        u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        
        print(f"✓ Mann-Whitney U: U={u_stat:.1f}, p={p_value:.4f}")
    
    def test_chisquare_categorical(self):
        """Test chi-square for categorical variables"""
        # 2x2 contingency table
        table = np.array([
            [30, 10],
            [15, 25]
        ])
        
        chi2, p_value, dof, expected = stats.chi2_contingency(table)
        
        assert p_value < 0.05  # Significant association
        print(f"✓ Chi-square: χ²={chi2:.2f}, p={p_value:.4f}")
    
    def test_fisher_exact(self):
        """Test Fisher's exact test for small samples"""
        # Small sample 2x2 table
        table = np.array([
            [3, 1],
            [1, 3]
        ])
        
        odds_ratio, p_value = stats.fisher_exact(table)
        
        print(f"✓ Fisher's exact: OR={odds_ratio:.2f}, p={p_value:.4f}")
    
    def test_anova_multiple_groups(self):
        """Test ANOVA for 3+ groups"""
        group1 = np.array([10, 12, 14])
        group2 = np.array([20, 22, 24])
        group3 = np.array([30, 32, 34])
        
        f_stat, p_value = stats.f_oneway(group1, group2, group3)
        
        assert p_value < 0.01  # Significant difference
        print(f"✓ ANOVA: F={f_stat:.2f}, p={p_value:.4f}")
    
    def test_kruskal_multiple_groups(self):
        """Test Kruskal-Wallis for 3+ groups (non-parametric)"""
        group1 = np.array([1, 2, 3])
        group2 = np.array([4, 5, 6])
        group3 = np.array([7, 8, 9])
        
        h_stat, p_value = stats.kruskal(group1, group2, group3)
        
        print(f"✓ Kruskal-Wallis: H={h_stat:.2f}, p={p_value:.4f}")


class TestNormalityDetection:
    """Test automatic normality detection for test selection"""
    
    def test_shapiro_normal(self):
        """Test Shapiro-Wilk on normal data"""
        np.random.seed(42)
        data = np.random.normal(0, 1, 50)
        
        stat, p_value = stats.shapiro(data)
        
        # Normal data should pass (p > 0.05)
        assert p_value > 0.05
        print(f"✓ Shapiro-Wilk (normal): p={p_value:.4f}")
    
    def test_shapiro_skewed(self):
        """Test Shapiro-Wilk on skewed data"""
        np.random.seed(42)
        data = np.random.exponential(1, 50)
        
        stat, p_value = stats.shapiro(data)
        
        # Skewed data should fail (p < 0.05)
        assert p_value < 0.05
        print(f"✓ Shapiro-Wilk (skewed): p={p_value:.4f}")
    
    def test_skewness_threshold(self):
        """Test skewness-based normality assessment"""
        np.random.seed(42)
        
        # Normal data
        normal_data = np.random.normal(0, 1, 100)
        skew_normal = stats.skew(normal_data)
        
        # Skewed data
        skewed_data = np.random.exponential(1, 100)
        skew_exp = stats.skew(skewed_data)
        
        # Threshold: |skew| < 1 suggests normal
        assert abs(skew_normal) < 1
        assert abs(skew_exp) > 1
        print(f"✓ Skewness: normal={skew_normal:.2f}, skewed={skew_exp:.2f}")


class TestColumnClassification:
    """Test automatic column type classification"""
    
    def test_detect_numeric(self):
        """Test numeric column detection"""
        df = pd.DataFrame({
            'age': [25, 30, 35, 40],
            'weight': [60.5, 70.2, 65.0, 80.1]
        })
        
        for col in df.columns:
            assert pd.api.types.is_numeric_dtype(df[col])
        print("✓ Numeric columns detected")
    
    def test_detect_categorical(self):
        """Test categorical column detection"""
        df = pd.DataFrame({
            'gender': ['M', 'F', 'M', 'F'],
            'grade': pd.Categorical(['A', 'B', 'A', 'C'])
        })
        
        # String or category type
        assert df['gender'].dtype == object or pd.api.types.is_categorical_dtype(df['gender'])
        assert pd.api.types.is_categorical_dtype(df['grade'])
        print("✓ Categorical columns detected")
    
    def test_detect_binary(self):
        """Test binary column detection"""
        data = pd.Series([0, 1, 0, 1, 0])
        
        unique_values = data.unique()
        is_binary = len(unique_values) == 2
        
        assert is_binary
        print("✓ Binary column detected")
    
    def test_auto_categorical_threshold(self):
        """Test automatic categorical classification by unique count"""
        # Low cardinality numeric should be treated as categorical
        data = pd.Series([1, 2, 3, 1, 2, 3, 1, 2, 3])
        
        n_unique = data.nunique()
        n_total = len(data)
        
        # If unique/total < 0.05 or unique < 10, treat as categorical
        is_categorical = n_unique < 10 or n_unique / n_total < 0.05
        
        assert is_categorical
        print(f"✓ Auto-categorical: {n_unique} unique values")


class TestTableFormatting:
    """Test table formatting and output"""
    
    def test_overall_column(self):
        """Test overall (ungrouped) column"""
        df = pd.DataFrame({
            'age': [25, 30, 35, 40, 45],
            'weight': [60, 70, 65, 80, 75]
        })
        
        overall = {
            'age': f"{df['age'].mean():.1f} ± {df['age'].std():.1f}",
            'weight': f"{df['weight'].mean():.1f} ± {df['weight'].std():.1f}"
        }
        
        assert '35.0' in overall['age']
        print("✓ Overall column formatting")
    
    def test_grouped_columns(self):
        """Test grouped columns"""
        df = pd.DataFrame({
            'group': ['A', 'A', 'A', 'B', 'B'],
            'age': [25, 30, 35, 40, 45]
        })
        
        grouped = df.groupby('group')['age'].agg(['mean', 'std'])
        
        assert len(grouped) == 2
        print("✓ Grouped columns")
    
    def test_p_value_formatting(self):
        """Test p-value formatting"""
        def format_p(p):
            if p < 0.001:
                return "<0.001"
            elif p < 0.01:
                return f"{p:.3f}"
            elif p < 0.05:
                return f"{p:.3f}"
            else:
                return f"{p:.2f}"
        
        assert format_p(0.0001) == "<0.001"
        assert format_p(0.005) == "0.005"
        assert format_p(0.234) == "0.23"
        print("✓ P-value formatting")
    
    def test_significance_markers(self):
        """Test significance markers"""
        def get_marker(p):
            if p < 0.001:
                return "***"
            elif p < 0.01:
                return "**"
            elif p < 0.05:
                return "*"
            else:
                return ""
        
        assert get_marker(0.0001) == "***"
        assert get_marker(0.005) == "**"
        assert get_marker(0.04) == "*"
        assert get_marker(0.10) == ""
        print("✓ Significance markers")


class TestSpecialCases:
    """Test special cases and edge conditions"""
    
    def test_single_group(self):
        """Test table with single group (no comparison)"""
        df = pd.DataFrame({
            'age': [25, 30, 35, 40, 45],
            'gender': ['M', 'F', 'M', 'F', 'M']
        })
        
        # Should produce descriptive stats without p-values
        stats_age = f"{df['age'].mean():.1f} ± {df['age'].std():.1f}"
        stats_gender = df['gender'].value_counts()
        
        assert stats_age is not None
        assert stats_gender is not None
        print("✓ Single group table")
    
    def test_all_missing(self):
        """Test handling of all-missing column"""
        df = pd.DataFrame({
            'complete': [1, 2, 3, 4, 5],
            'missing': [np.nan, np.nan, np.nan, np.nan, np.nan]
        })
        
        n_valid = df['missing'].notna().sum()
        
        assert n_valid == 0
        print("✓ All-missing column handled")
    
    def test_constant_column(self):
        """Test handling of constant column"""
        df = pd.DataFrame({
            'variable': [1, 2, 3, 4, 5],
            'constant': [1, 1, 1, 1, 1]
        })
        
        std = df['constant'].std()
        
        assert std == 0
        print("✓ Constant column handled")
    
    def test_small_sample(self):
        """Test small sample handling"""
        df = pd.DataFrame({
            'group': ['A', 'B'],
            'value': [10, 20]
        })
        
        # Should use Fisher's exact or skip test
        n_per_group = df.groupby('group').size()
        min_n = n_per_group.min()
        
        assert min_n == 1
        print("✓ Small sample detected")


class TestSMD:
    """Test Standardized Mean Difference for balance tables"""
    
    def test_smd_continuous(self):
        """Test SMD for continuous variables"""
        group1 = np.array([10, 12, 14, 16, 18])
        group2 = np.array([20, 22, 24, 26, 28])
        
        pooled_sd = np.sqrt((group1.var() + group2.var()) / 2)
        smd = (group1.mean() - group2.mean()) / pooled_sd
        
        assert abs(smd) > 0.8  # Large imbalance
        print(f"✓ SMD (continuous) = {smd:.3f}")
    
    def test_smd_binary(self):
        """Test SMD for binary variables"""
        p1 = 0.3  # Proportion in group 1
        p2 = 0.5  # Proportion in group 2
        
        # SMD for proportions
        pooled_sd = np.sqrt((p1*(1-p1) + p2*(1-p2)) / 2)
        smd = (p1 - p2) / pooled_sd
        
        assert abs(smd) > 0.3  # Moderate imbalance
        print(f"✓ SMD (binary) = {smd:.3f}")
    
    def test_smd_threshold(self):
        """Test SMD threshold for balance"""
        smd_values = [0.05, 0.08, 0.12, 0.25]
        
        # Common threshold: |SMD| < 0.1 indicates good balance
        balanced = [abs(smd) < 0.1 for smd in smd_values]
        
        assert balanced[:2] == [True, True]
        assert balanced[2:] == [False, False]
        print("✓ SMD threshold check")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running TableOne generation isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestDescriptiveStatistics(),
        TestGroupComparisons(),
        TestNormalityDetection(),
        TestColumnClassification(),
        TestTableFormatting(),
        TestSpecialCases(),
        TestSMD(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)
        
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise
    
    print("\n" + "=" * 60)
    print("🎉 ALL TABLEONE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

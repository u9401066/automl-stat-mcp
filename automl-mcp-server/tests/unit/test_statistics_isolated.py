"""
Isolated tests for statistical analysis utilities.

Tests the core statistics logic used in statistics_tools.py
without requiring the full MCP stack.
"""

import numpy as np
import pandas as pd
from scipy import stats


class TestDescriptiveStatistics:
    """Test descriptive statistics calculations"""

    def test_basic_stats_numeric(self):
        """Test basic numeric statistics"""
        data = [10, 20, 30, 40, 50]

        mean = np.mean(data)
        std = np.std(data, ddof=1)  # Sample std
        median = np.median(data)
        min_val = np.min(data)
        max_val = np.max(data)

        assert mean == 30
        assert abs(std - 15.81) < 0.01
        assert median == 30
        assert min_val == 10
        assert max_val == 50
        print("✓ Basic numeric statistics")

    def test_percentiles(self):
        """Test percentile calculations"""
        data = np.arange(1, 101)  # 1 to 100

        p25 = np.percentile(data, 25)
        p50 = np.percentile(data, 50)
        p75 = np.percentile(data, 75)

        assert p25 == 25.75
        assert p50 == 50.5
        assert p75 == 75.25
        print("✓ Percentile calculations")

    def test_skewness_kurtosis(self):
        """Test skewness and kurtosis"""
        # Normal distribution should have ~0 skewness and ~0 excess kurtosis
        np.random.seed(42)
        normal_data = np.random.normal(0, 1, 10000)

        skew = stats.skew(normal_data)
        kurt = stats.kurtosis(normal_data)  # Fisher definition (excess)

        assert abs(skew) < 0.1  # Close to 0
        assert abs(kurt) < 0.2  # Close to 0 for normal
        print("✓ Skewness and kurtosis for normal distribution")

    def test_skewed_distribution(self):
        """Test skewness detection"""
        # Right-skewed data (exponential)
        np.random.seed(42)
        skewed_data = np.random.exponential(1, 1000)

        skew = stats.skew(skewed_data)
        assert skew > 1.5  # Exponential has positive skew ~2
        print("✓ Detected positive skewness")


class TestCorrelationAnalysis:
    """Test correlation calculations"""

    def test_pearson_correlation(self):
        """Test Pearson correlation"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation

        r, p = stats.pearsonr(x, y)
        assert abs(r - 1.0) < 0.0001
        assert p < 0.05
        print("✓ Pearson correlation (perfect positive)")

    def test_spearman_correlation(self):
        """Test Spearman rank correlation"""
        x = [1, 2, 3, 4, 5]
        y = [1, 8, 27, 64, 125]  # Monotonic but non-linear (cubed)

        rho, p = stats.spearmanr(x, y)
        assert abs(rho - 1.0) < 0.0001  # Perfect monotonic
        print("✓ Spearman correlation (monotonic)")

    def test_negative_correlation(self):
        """Test negative correlation detection"""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]  # Perfect negative

        r, p = stats.pearsonr(x, y)
        assert abs(r - (-1.0)) < 0.0001
        print("✓ Negative correlation detected")

    def test_no_correlation(self):
        """Test no correlation"""
        np.random.seed(42)
        x = np.random.randn(100)
        y = np.random.randn(100)

        r, p = stats.pearsonr(x, y)
        assert abs(r) < 0.3  # Should be weak
        print("✓ No correlation (random data)")

    def test_correlation_matrix(self):
        """Test correlation matrix calculation"""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [2, 4, 6, 8, 10],  # Perfect with a
                "c": [5, 4, 3, 2, 1],  # Perfect negative with a
            }
        )

        corr_matrix = df.corr()

        assert abs(corr_matrix.loc["a", "b"] - 1.0) < 0.0001
        assert abs(corr_matrix.loc["a", "c"] - (-1.0)) < 0.0001
        assert abs(corr_matrix.loc["b", "c"] - (-1.0)) < 0.0001
        print("✓ Correlation matrix calculation")


class TestNormalityTests:
    """Test normality testing"""

    def test_shapiro_wilk_normal(self):
        """Test Shapiro-Wilk on normal data"""
        np.random.seed(42)
        normal_data = np.random.normal(0, 1, 50)

        stat, p = stats.shapiro(normal_data)
        assert p > 0.05  # Should not reject normality
        print("✓ Shapiro-Wilk: normal data passes")

    def test_shapiro_wilk_nonnormal(self):
        """Test Shapiro-Wilk on non-normal data"""
        np.random.seed(42)
        nonnormal_data = np.random.exponential(1, 50)

        stat, p = stats.shapiro(nonnormal_data)
        assert p < 0.05  # Should reject normality
        print("✓ Shapiro-Wilk: non-normal data rejected")

    def test_dagostino_normal(self):
        """Test D'Agostino-Pearson on normal data"""
        np.random.seed(42)
        normal_data = np.random.normal(0, 1, 100)

        stat, p = stats.normaltest(normal_data)
        assert p > 0.05
        print("✓ D'Agostino-Pearson: normal data passes")


class TestGroupComparisons:
    """Test group comparison tests"""

    def test_independent_ttest(self):
        """Test independent samples t-test"""
        group1 = [10, 12, 14, 16, 18]
        group2 = [20, 22, 24, 26, 28]

        t, p = stats.ttest_ind(group1, group2)
        assert p < 0.01  # Significantly different
        assert t < 0  # group1 < group2
        print("✓ Independent t-test: significant difference")

    def test_ttest_no_difference(self):
        """Test t-test with no difference"""
        np.random.seed(42)
        group1 = np.random.normal(50, 10, 30)
        group2 = np.random.normal(50, 10, 30)

        t, p = stats.ttest_ind(group1, group2)
        assert p > 0.05  # Not significantly different
        print("✓ T-test: no significant difference")

    def test_paired_ttest(self):
        """Test paired t-test (before/after)"""
        before = [100, 120, 110, 115, 105]
        after = [90, 100, 95, 100, 90]  # All decreased

        t, p = stats.ttest_rel(before, after)
        assert p < 0.05  # Significant decrease
        assert t > 0  # before > after
        print("✓ Paired t-test: significant change")

    def test_mann_whitney_u(self):
        """Test Mann-Whitney U (non-parametric)"""
        group1 = [1, 2, 3, 4, 5]
        group2 = [6, 7, 8, 9, 10]

        stat, p = stats.mannwhitneyu(group1, group2, alternative="two-sided")
        assert p < 0.05  # Significantly different distributions
        print("✓ Mann-Whitney U: significant difference")

    def test_one_way_anova(self):
        """Test one-way ANOVA"""
        group1 = [10, 12, 14]
        group2 = [20, 22, 24]
        group3 = [30, 32, 34]

        f, p = stats.f_oneway(group1, group2, group3)
        assert p < 0.001  # Significantly different
        assert f > 10  # Large F statistic
        print("✓ One-way ANOVA: significant difference")

    def test_kruskal_wallis(self):
        """Test Kruskal-Wallis (non-parametric ANOVA)"""
        group1 = [1, 2, 3]
        group2 = [4, 5, 6]
        group3 = [7, 8, 9]

        h, p = stats.kruskal(group1, group2, group3)
        assert p < 0.05
        print("✓ Kruskal-Wallis: significant difference")


class TestChiSquareTests:
    """Test chi-square tests"""

    def test_chi_square_independence(self):
        """Test chi-square test of independence"""
        # Strong association
        contingency = np.array(
            [
                [50, 10],  # Group A: mostly outcome 1
                [10, 50],  # Group B: mostly outcome 2
            ]
        )

        chi2, p, dof, expected = stats.chi2_contingency(contingency)
        assert p < 0.001  # Strong association
        assert chi2 > 30
        print("✓ Chi-square: strong association detected")

    def test_chi_square_no_association(self):
        """Test chi-square with no association"""
        contingency = np.array([[25, 25], [25, 25]])

        chi2, p, dof, expected = stats.chi2_contingency(contingency)
        assert p > 0.9  # No association
        assert chi2 < 0.01
        print("✓ Chi-square: no association")

    def test_cramers_v(self):
        """Test Cramér's V effect size"""
        contingency = np.array([[50, 10], [10, 50]])

        chi2, p, dof, expected = stats.chi2_contingency(contingency)
        n = contingency.sum()
        min_dim = min(contingency.shape) - 1

        cramers_v = np.sqrt(chi2 / (n * min_dim))
        assert cramers_v > 0.6  # Strong effect
        print(f"✓ Cramér's V = {cramers_v:.3f}")


class TestEffectSizes:
    """Test effect size calculations"""

    def test_cohens_d(self):
        """Test Cohen's d calculation"""
        group1 = np.array([10, 12, 14, 16, 18])
        group2 = np.array([20, 22, 24, 26, 28])

        # Cohen's d = (mean1 - mean2) / pooled_std
        mean1, mean2 = group1.mean(), group2.mean()
        n1, n2 = len(group1), len(group2)

        var1 = group1.var(ddof=1)
        var2 = group2.var(ddof=1)

        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        cohens_d = (mean1 - mean2) / pooled_std

        assert abs(cohens_d) > 2.0  # Very large effect
        print(f"✓ Cohen's d = {cohens_d:.3f}")

    def test_effect_size_interpretation(self):
        """Test effect size interpretation"""

        def interpret_cohens_d(d):
            d = abs(d)
            if d < 0.2:
                return "negligible"
            elif d < 0.5:
                return "small"
            elif d < 0.8:
                return "medium"
            else:
                return "large"

        assert interpret_cohens_d(0.1) == "negligible"
        assert interpret_cohens_d(0.3) == "small"
        assert interpret_cohens_d(0.6) == "medium"
        assert interpret_cohens_d(1.0) == "large"
        print("✓ Effect size interpretation")


class TestRegressionAnalysis:
    """Test simple regression analysis"""

    def test_simple_linear_regression(self):
        """Test simple linear regression"""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2.1, 4.0, 5.9, 8.1, 10.0])  # y ≈ 2x

        slope, intercept, r, p, se = stats.linregress(x, y)

        assert abs(slope - 2.0) < 0.1  # Slope ≈ 2
        assert abs(intercept) < 0.5  # Intercept ≈ 0
        assert r > 0.99  # High correlation
        assert p < 0.001  # Significant
        print(f"✓ Linear regression: y = {slope:.2f}x + {intercept:.2f}, R²={r**2:.3f}")

    def test_r_squared(self):
        """Test R-squared interpretation"""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 4, 6, 8, 10])  # Perfect linear

        slope, intercept, r, p, se = stats.linregress(x, y)
        r_squared = r**2

        assert abs(r_squared - 1.0) < 0.0001  # Perfect fit
        print(f"✓ R² = {r_squared:.4f}")


class TestOutlierDetection:
    """Test outlier detection methods"""

    def test_iqr_method(self):
        """Test IQR outlier detection"""
        data = [10, 12, 14, 15, 16, 18, 20, 100]  # 100 is outlier

        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = [x for x in data if x < lower or x > upper]
        assert 100 in outliers
        print(f"✓ IQR method detected outlier: {outliers}")

    def test_zscore_method(self):
        """Test Z-score outlier detection"""
        np.random.seed(42)
        data = list(np.random.normal(50, 10, 100)) + [150]  # Add outlier

        z_scores = np.abs(stats.zscore(data))
        threshold = 3

        outlier_indices = np.where(z_scores > threshold)[0]
        assert len(outlier_indices) > 0
        assert 100 in outlier_indices  # Last element is outlier
        print(f"✓ Z-score method detected {len(outlier_indices)} outlier(s)")


class TestConfidenceIntervals:
    """Test confidence interval calculations"""

    def test_mean_ci(self):
        """Test confidence interval for mean"""
        np.random.seed(42)
        data = np.random.normal(100, 15, 50)

        mean = np.mean(data)
        sem = stats.sem(data)
        ci = stats.t.interval(0.95, len(data) - 1, loc=mean, scale=sem)

        assert ci[0] < mean < ci[1]  # Mean is in CI
        assert 100 > ci[0] and 100 < ci[1]  # True mean in CI
        print(f"✓ 95% CI for mean: [{ci[0]:.2f}, {ci[1]:.2f}]")

    def test_proportion_ci(self):
        """Test confidence interval for proportion"""
        # Wilson score interval
        successes = 75
        total = 100
        p = successes / total

        # Normal approximation
        z = 1.96
        se = np.sqrt(p * (1 - p) / total)
        ci = (p - z * se, p + z * se)

        assert 0.65 < ci[0] < p
        assert p < ci[1] < 0.85
        print(f"✓ 95% CI for proportion: [{ci[0]:.3f}, {ci[1]:.3f}]")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running statistics utilities isolated tests")
    print("=" * 60)

    test_classes = [
        TestDescriptiveStatistics(),
        TestCorrelationAnalysis(),
        TestNormalityTests(),
        TestGroupComparisons(),
        TestChiSquareTests(),
        TestEffectSizes(),
        TestRegressionAnalysis(),
        TestOutlierDetection(),
        TestConfidenceIntervals(),
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)

        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise

    print("\n" + "=" * 60)
    print("🎉 ALL STATISTICS TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

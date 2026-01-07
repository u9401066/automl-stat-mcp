"""
Unit tests for advanced analysis module (Phase 1 enhancements).

Tests:
- Enhanced correlation analysis with significance testing
- Distribution comparison tests (KS, Levene, normality)
- Missing value analysis (MCAR/MAR/MNAR detection)
- VIF multicollinearity detection
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.advanced_analysis import (
    EnhancedCorrelationResult,
    GroupComparisonResult,
    MissingValueAnalysis,
    MulticollinearityAnalysis,
    analyze_missing_values,
    compare_distributions,
    compute_enhanced_correlation,
    compute_vif,
    run_enhanced_analysis,
)

# ============================================================
# Test Data Fixtures
# ============================================================

@pytest.fixture
def sample_numeric_df():
    """Sample DataFrame with numeric columns for correlation tests."""
    np.random.seed(42)
    n = 100
    x = np.random.randn(n)
    y = x * 0.8 + np.random.randn(n) * 0.5  # Correlated with x
    z = np.random.randn(n)  # Independent
    return pd.DataFrame({'x': x, 'y': y, 'z': z})


@pytest.fixture
def sample_with_groups():
    """Sample DataFrame with numeric column and group column."""
    np.random.seed(42)
    groups = np.repeat(['A', 'B', 'C'], 40)
    # Group means: A=0, B=2, C=5
    values = np.concatenate([
        np.random.randn(40) * 1,
        np.random.randn(40) * 1 + 2,
        np.random.randn(40) * 1 + 5,
    ])
    return pd.DataFrame({'value': values, 'group': groups})


@pytest.fixture
def sample_with_missing():
    """Sample DataFrame with various missing value patterns."""
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'complete': np.random.randn(n),
        'random_missing': np.random.randn(n),
        'systematic_missing': np.random.randn(n),
        'high_missing': np.random.randn(n),
    })
    # Random missing (~10%)
    mask = np.random.random(n) < 0.1
    df.loc[mask, 'random_missing'] = np.nan

    # Systematic missing (when complete > 0)
    df.loc[df['complete'] > 0, 'systematic_missing'] = np.nan

    # High missing (~60%)
    mask = np.random.random(n) < 0.6
    df.loc[mask, 'high_missing'] = np.nan

    return df


@pytest.fixture
def sample_collinear():
    """Sample DataFrame with collinear features."""
    np.random.seed(42)
    n = 100
    x1 = np.random.randn(n)
    x2 = x1 * 0.95 + np.random.randn(n) * 0.1  # Highly correlated with x1
    x3 = np.random.randn(n)  # Independent
    y = x1 + x3 + np.random.randn(n) * 0.5
    return pd.DataFrame({'x1': x1, 'x2': x2, 'x3': x3, 'y': y})


# ============================================================
# Test Enhanced Correlation Analysis
# ============================================================

class TestEnhancedCorrelation:
    """Tests for enhanced correlation analysis."""

    def test_compute_correlation_basic(self, sample_numeric_df):
        """Test basic correlation computation."""
        result = compute_enhanced_correlation(sample_numeric_df)

        assert isinstance(result, EnhancedCorrelationResult)
        assert result.pearson_matrix is not None
        assert result.pearson_pvalue_matrix is not None
        assert result.n_samples > 0

    def test_correlation_values(self, sample_numeric_df):
        """Test that x and y are significantly correlated."""
        result = compute_enhanced_correlation(sample_numeric_df)

        # x and y should be strongly correlated
        corr_xy = result.pearson_matrix['x']['y']
        assert abs(corr_xy) > 0.5

    def test_pvalue_matrix(self, sample_numeric_df):
        """Test p-value computation."""
        result = compute_enhanced_correlation(sample_numeric_df)

        # p-value for x-y should be low (significant)
        p_xy = result.pearson_pvalue_matrix['x']['y']
        assert p_xy < 0.05

    def test_significant_pairs(self, sample_numeric_df):
        """Test significant pairs extraction."""
        result = compute_enhanced_correlation(sample_numeric_df)

        # Should find x-y as significant pair
        assert len(result.significant_pairs) > 0
        var_pairs = [(p.var1, p.var2) for p in result.significant_pairs]
        assert ('x', 'y') in var_pairs or ('y', 'x') in var_pairs

    def test_heatmap_data(self, sample_numeric_df):
        """Test heatmap-ready data format."""
        result = compute_enhanced_correlation(sample_numeric_df)

        assert result.heatmap_data is not None
        assert len(result.heatmap_data) > 0

        # Check heatmap item structure
        item = result.heatmap_data[0]
        assert 'x' in item
        assert 'y' in item
        assert 'value' in item
        assert 'row' in item
        assert 'col' in item

    def test_summary_statistics(self, sample_numeric_df):
        """Test summary statistics."""
        result = compute_enhanced_correlation(sample_numeric_df)

        assert result.summary is not None
        assert 'n_variables' in result.summary
        assert 'n_pairs' in result.summary
        assert 'n_significant' in result.summary

    def test_to_dict(self, sample_numeric_df):
        """Test to_dict method."""
        result = compute_enhanced_correlation(sample_numeric_df)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'matrices' in result_dict
        assert 'significant_pairs' in result_dict
        assert 'heatmap_data' in result_dict

    def test_spearman_correlation(self, sample_numeric_df):
        """Test Spearman correlation computation."""
        result = compute_enhanced_correlation(sample_numeric_df, method='all')

        assert result.spearman_matrix is not None
        assert result.spearman_pvalue_matrix is not None


# ============================================================
# Test Distribution Comparison
# ============================================================

class TestDistributionComparison:
    """Tests for distribution comparison."""

    def test_two_group_comparison(self, sample_with_groups):
        """Test comparison between two groups."""
        # Filter to just 2 groups
        df = sample_with_groups[sample_with_groups['group'].isin(['A', 'C'])]

        result = compare_distributions(df, 'value', 'group')

        assert isinstance(result, GroupComparisonResult)
        assert result.main_test is not None
        assert result.main_test.p_value < 0.05  # Groups A and C are different

    def test_multi_group_comparison(self, sample_with_groups):
        """Test comparison across multiple groups."""
        result = compare_distributions(sample_with_groups, 'value', 'group')

        assert result.main_test is not None
        assert result.main_test.test_name in ['One-way ANOVA', 'Kruskal-Wallis H', 'Independent t-test', 'Mann-Whitney U']
        assert result.main_test.p_value < 0.05  # Groups are different

    def test_normality_results(self, sample_with_groups):
        """Test normality test results."""
        result = compare_distributions(sample_with_groups, 'value', 'group')

        assert result.normality_tests is not None

    def test_group_statistics(self, sample_with_groups):
        """Test group-level statistics."""
        result = compare_distributions(sample_with_groups, 'value', 'group')

        assert result.group_stats is not None
        assert len(result.group_stats) == 3  # 3 groups

    def test_to_dict(self, sample_with_groups):
        """Test to_dict method."""
        result = compare_distributions(sample_with_groups, 'value', 'group')
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'main_test' in result_dict
        assert 'groups' in result_dict
        assert 'normality' in result_dict


# ============================================================
# Test Missing Value Analysis
# ============================================================

class TestMissingValueAnalysis:
    """Tests for missing value analysis."""

    def test_missing_summary(self, sample_with_missing):
        """Test missing value summary statistics."""
        result = analyze_missing_values(sample_with_missing)

        assert isinstance(result, MissingValueAnalysis)
        assert result.column_missing is not None

        # Complete column should not be in column_missing (no missing)
        assert 'complete' not in result.column_missing

    def test_high_missing_detection(self, sample_with_missing):
        """Test detection of columns with high missing rates."""
        result = analyze_missing_values(sample_with_missing)

        # high_missing column should be in column_missing
        assert 'high_missing' in result.column_missing
        assert result.column_missing['high_missing']['pct_missing'] > 50

    def test_total_missing_rate(self, sample_with_missing):
        """Test total missing rate calculation."""
        result = analyze_missing_values(sample_with_missing)

        assert result.missing_pct is not None
        assert 0 < result.missing_pct < 100  # Some but not all missing

    def test_pattern_analysis(self, sample_with_missing):
        """Test missing pattern analysis."""
        result = analyze_missing_values(sample_with_missing)

        assert result.missing_pattern is not None
        assert result.missing_pattern in ['MCAR', 'MAR', 'MNAR', 'unknown', 'none', 'mixed']

    def test_recommendations(self, sample_with_missing):
        """Test missing value recommendations."""
        result = analyze_missing_values(sample_with_missing)

        assert result.recommendations is not None
        assert len(result.recommendations) > 0

    def test_to_dict(self, sample_with_missing):
        """Test to_dict method."""
        result = analyze_missing_values(sample_with_missing)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'columns' in result_dict
        assert 'summary' in result_dict
        assert 'pattern' in result_dict


# ============================================================
# Test VIF Multicollinearity
# ============================================================

class TestVIFMulticollinearity:
    """Tests for VIF multicollinearity detection."""

    def test_vif_basic(self, sample_collinear):
        """Test basic VIF computation."""
        features = ['x1', 'x2', 'x3']

        result = compute_vif(sample_collinear, features)

        assert isinstance(result, MulticollinearityAnalysis)
        assert result.vif_results is not None
        assert len(result.vif_results) == 3

    def test_high_vif_detection(self, sample_collinear):
        """Test detection of high VIF (collinear) features."""
        features = ['x1', 'x2', 'x3']

        result = compute_vif(sample_collinear, features)

        # x1 and x2 should have high VIF (collinear)
        assert result.problematic_columns is not None
        assert 'x1' in result.problematic_columns or 'x2' in result.problematic_columns

    def test_low_vif_for_independent(self, sample_collinear):
        """Test that independent variable has low VIF."""
        features = ['x1', 'x2', 'x3']

        result = compute_vif(sample_collinear, features)

        # x3 should have low VIF (independent)
        x3_vif = None
        for vr in result.vif_results:
            if vr.column == 'x3':
                x3_vif = vr.vif
                break

        assert x3_vif is not None
        assert x3_vif < 5.0  # Low VIF threshold

    def test_recommendations(self, sample_collinear):
        """Test removal recommendations for collinear features."""
        features = ['x1', 'x2', 'x3']

        result = compute_vif(sample_collinear, features)

        assert result.recommendations is not None

    def test_to_dict(self, sample_collinear):
        """Test to_dict method."""
        features = ['x1', 'x2', 'x3']

        result = compute_vif(sample_collinear, features)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'vif_results' in result_dict
        assert 'problematic_columns' in result_dict


# ============================================================
# Test run_enhanced_analysis (Integration)
# ============================================================

class TestRunEnhancedAnalysis:
    """Integration tests for run_enhanced_analysis."""

    def test_full_analysis(self, sample_with_missing):
        """Test full enhanced analysis."""
        # Add a group column for distribution tests
        df = sample_with_missing.copy()
        df['group'] = np.tile(['A', 'B'], len(df) // 2)

        result = run_enhanced_analysis(
            df,
            target_column='group',
            include_vif=True,
            include_missing_analysis=True,
        )

        assert isinstance(result, dict)
        assert 'correlation_analysis' in result or 'missing_analysis' in result

    def test_selective_analysis_no_vif(self, sample_numeric_df):
        """Test selective analysis (no VIF)."""
        result = run_enhanced_analysis(
            sample_numeric_df,
            include_vif=False,
            include_missing_analysis=False,
        )

        assert isinstance(result, dict)
        # Should have correlation analysis (always included for numeric df)
        assert 'correlation_analysis' in result

    def test_missing_only(self, sample_with_missing):
        """Test missing value analysis only."""
        result = run_enhanced_analysis(
            sample_with_missing,
            include_vif=False,
            include_missing_analysis=True,
        )

        assert isinstance(result, dict)
        assert 'missing_analysis' in result

    def test_error_handling_empty_df(self):
        """Test error handling for empty DataFrame."""
        df = pd.DataFrame()

        result = run_enhanced_analysis(df)
        # Should return dict, not crash (maybe empty or with error)
        assert isinstance(result, dict)


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_column(self):
        """Test with single column (no correlation possible)."""
        df = pd.DataFrame({'x': [1, 2, 3, 4, 5]})
        result = compute_enhanced_correlation(df)

        # Should handle gracefully
        assert isinstance(result, EnhancedCorrelationResult)

    def test_all_missing(self):
        """Test with all missing values."""
        df = pd.DataFrame({
            'x': [np.nan] * 10,
            'y': [np.nan] * 10,
        })
        result = analyze_missing_values(df)

        # Should handle gracefully
        assert isinstance(result, MissingValueAnalysis)

    def test_constant_column(self, sample_numeric_df):
        """Test with constant column (zero variance)."""
        df = sample_numeric_df.copy()
        df['constant'] = 1.0

        result = compute_enhanced_correlation(df)
        # Should handle gracefully without crashing
        assert isinstance(result, EnhancedCorrelationResult)

    def test_small_sample(self):
        """Test with very small sample size."""
        df = pd.DataFrame({
            'x': [1, 2, 3],
            'y': [4, 5, 6],
        })
        result = compute_enhanced_correlation(df)

        # Should handle gracefully
        assert isinstance(result, EnhancedCorrelationResult)


# ============================================================
# Run tests
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

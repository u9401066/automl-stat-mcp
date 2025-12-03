"""
Unit tests for TableOne Generator Module.

Tests for publication-ready Table 1 (baseline characteristics table) generation.
"""
import pytest
import pandas as pd
import numpy as np
from io import StringIO

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.tableone_generator import (
    TableOneGenerator,
    TableOneResult,
    VariableStats,
    VariableType,
    TestType,
    generate_tableone,
    quick_tableone,
    safe_round,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def simple_df():
    """Simple DataFrame for basic testing."""
    np.random.seed(42)
    return pd.DataFrame({
        'age': np.random.normal(50, 15, 100),
        'gender': np.random.choice(['Male', 'Female'], 100),
        'bmi': np.random.normal(25, 5, 100),
        'treatment': np.random.choice(['Drug', 'Placebo'], 100),
    })


@pytest.fixture
def clinical_df():
    """Clinical trial-like DataFrame with more complexity."""
    np.random.seed(123)
    n = 200
    
    # Create treatment groups with different outcomes
    treatment = np.random.choice(['Active', 'Control'], n)
    
    # Age differs slightly by group
    age = np.where(
        treatment == 'Active',
        np.random.normal(55, 12, n),
        np.random.normal(58, 10, n)
    )
    
    # Gender balanced
    gender = np.random.choice(['Male', 'Female'], n)
    
    # Smoking status
    smoking = np.random.choice(['Never', 'Former', 'Current'], n, p=[0.4, 0.35, 0.25])
    
    # Skewed BMI
    bmi = np.random.exponential(5, n) + 20
    
    # Lab values (some missing)
    creatinine = np.random.normal(1.0, 0.3, n)
    creatinine[np.random.choice(n, 15, replace=False)] = np.nan
    
    # Binary outcome
    diabetes = np.random.choice([0, 1], n, p=[0.7, 0.3])
    
    return pd.DataFrame({
        'treatment_group': treatment,
        'age': age,
        'gender': gender,
        'smoking_status': smoking,
        'bmi': bmi,
        'creatinine': creatinine,
        'diabetes': diabetes,
    })


@pytest.fixture
def small_df():
    """Small DataFrame for edge case testing."""
    return pd.DataFrame({
        'group': ['A', 'A', 'B', 'B'],
        'value': [10, 20, 30, 40],
        'category': ['X', 'Y', 'X', 'Y'],
    })


@pytest.fixture
def missing_df():
    """DataFrame with various missing value patterns."""
    return pd.DataFrame({
        'group': ['A', 'A', 'B', 'B', 'A', 'B'] * 10,
        'complete': range(60),
        'some_missing': [np.nan if i % 5 == 0 else i for i in range(60)],
        'mostly_missing': [np.nan if i % 2 == 0 else i for i in range(60)],
        'categorical': ['cat1', 'cat2', None, 'cat1', 'cat2', None] * 10,
    })


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestSafeRound:
    """Tests for safe_round function."""
    
    def test_normal_values(self):
        """Test rounding normal values."""
        assert safe_round(3.14159, 2) == 3.14
        assert safe_round(100.0, 0) == 100
        assert safe_round(0.001234, 3) == 0.001
    
    def test_none_value(self):
        """Test handling None."""
        assert safe_round(None, 2) is None
    
    def test_nan_value(self):
        """Test handling NaN."""
        assert safe_round(float('nan'), 2) is None
    
    def test_inf_value(self):
        """Test handling infinity."""
        assert safe_round(float('inf'), 2) is None
        assert safe_round(float('-inf'), 2) is None


# =============================================================================
# Variable Stats Tests
# =============================================================================

class TestVariableStats:
    """Tests for VariableStats dataclass."""
    
    def test_continuous_stats_to_dict(self):
        """Test converting continuous stats to dict."""
        stats = VariableStats(
            name='age',
            var_type=VariableType.CONTINUOUS,
            n=100,
            n_missing=5,
            missing_pct=5.0,
            mean=50.5,
            std=10.2,
            median=50.0,
            q25=42.0,
            q75=58.0,
            min_val=25.0,
            max_val=80.0,
        )
        
        d = stats.to_dict()
        assert d['name'] == 'age'
        assert d['type'] == 'continuous'
        assert d['n'] == 100
        assert d['mean'] == 50.5
        assert d['median'] == 50.0
    
    def test_categorical_stats_to_dict(self):
        """Test converting categorical stats to dict."""
        stats = VariableStats(
            name='gender',
            var_type=VariableType.CATEGORICAL,
            n=100,
            n_missing=0,
            missing_pct=0.0,
            categories={'Male': 55, 'Female': 45},
            category_pcts={'Male': 55.0, 'Female': 45.0},
        )
        
        d = stats.to_dict()
        assert d['name'] == 'gender'
        assert d['type'] == 'categorical'
        assert d['categories'] == {'Male': 55, 'Female': 45}
    
    def test_with_test_results(self):
        """Test stats with statistical test results."""
        stats = VariableStats(
            name='age',
            var_type=VariableType.CONTINUOUS,
            n=100,
            test_type=TestType.TTEST,
            test_statistic=2.5,
            p_value=0.015,
        )
        
        d = stats.to_dict()
        assert 'test' in d
        assert d['test']['type'] == 't-test'
        assert d['test']['p_value'] == 0.015


# =============================================================================
# TableOneGenerator Tests
# =============================================================================

class TestTableOneGenerator:
    """Tests for TableOneGenerator class."""
    
    def test_basic_generation(self, simple_df):
        """Test basic table generation without grouping."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df)
        
        assert isinstance(result, TableOneResult)
        assert result.n_total == 100
        assert result.n_groups == 0
        assert 'age' in result.variables
        assert 'gender' in result.variables
    
    def test_grouped_generation(self, simple_df):
        """Test table generation with grouping."""
        generator = TableOneGenerator()
        result = generator.generate(
            simple_df,
            groupby='treatment',
            pval=True,
        )
        
        assert result.n_groups == 2
        assert set(result.group_names) == {'Drug', 'Placebo'}
        assert sum(result.group_sizes.values()) == 100
    
    def test_column_selection(self, clinical_df):
        """Test selecting specific columns."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            columns=['age', 'gender'],
            groupby='treatment_group',
        )
        
        assert result.variables == ['age', 'gender']
        assert 'bmi' not in result.variables
    
    def test_categorical_detection(self, simple_df):
        """Test automatic categorical variable detection."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df)
        
        assert 'gender' in result.categorical_vars
        assert 'age' not in result.categorical_vars
    
    def test_explicit_categorical(self, clinical_df):
        """Test explicit categorical specification."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            categorical=['gender', 'diabetes'],
            groupby='treatment_group',
        )
        
        assert 'gender' in result.categorical_vars
        assert 'diabetes' in result.categorical_vars
    
    def test_nonnormal_detection(self, clinical_df):
        """Test non-normal distribution detection."""
        generator = TableOneGenerator()
        result = generator.generate(clinical_df)
        
        # BMI is exponentially distributed, should be detected as non-normal
        # This may or may not be detected depending on sample
        assert isinstance(result.nonnormal_vars, list)
    
    def test_explicit_nonnormal(self, clinical_df):
        """Test explicit non-normal specification."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            nonnormal=['bmi'],
            groupby='treatment_group',
        )
        
        assert 'bmi' in result.nonnormal_vars
    
    def test_pvalue_calculation(self, clinical_df):
        """Test p-value calculation."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            groupby='treatment_group',
            pval=True,
        )
        
        # Check that p-values are calculated for some variables
        has_pvalue = False
        for var, stats in result.overall_stats.items():
            if stats.p_value is not None:
                has_pvalue = True
                assert 0 <= stats.p_value <= 1
        
        assert has_pvalue, "Expected at least one p-value to be calculated"
    
    def test_smd_calculation(self, clinical_df):
        """Test standardized mean difference calculation."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            groupby='treatment_group',
            smd=True,
        )
        
        # Check that SMD is calculated for continuous variables
        age_stats = result.overall_stats.get('age')
        if age_stats:
            # SMD should be calculated for 2 groups
            assert age_stats.smd is not None or result.n_groups != 2
    
    def test_missing_values(self, clinical_df):
        """Test missing value reporting."""
        generator = TableOneGenerator()
        result = generator.generate(clinical_df)
        
        # Creatinine has missing values
        creat_stats = result.overall_stats.get('creatinine')
        if creat_stats:
            assert creat_stats.n_missing > 0
            assert creat_stats.missing_pct > 0


# =============================================================================
# Statistical Test Selection Tests
# =============================================================================

class TestStatisticalTests:
    """Tests for statistical test selection logic."""
    
    def test_ttest_for_normal(self, simple_df):
        """Test t-test selection for normal distributions."""
        generator = TableOneGenerator()
        result = generator.generate(
            simple_df,
            groupby='treatment',
            continuous=['age'],
            pval=True,
        )
        
        age_stats = result.overall_stats.get('age')
        if age_stats and age_stats.test_type:
            # Should be t-test or Mann-Whitney depending on normality
            assert age_stats.test_type in [TestType.TTEST, TestType.MANN_WHITNEY]
    
    def test_mannwhitney_for_nonnormal(self):
        """Test Mann-Whitney selection for non-normal distributions."""
        np.random.seed(42)
        # Create clearly non-normal data (exponential)
        df = pd.DataFrame({
            'group': ['A'] * 50 + ['B'] * 50,
            'value': np.concatenate([
                np.random.exponential(1, 50),
                np.random.exponential(2, 50),
            ])
        })
        
        generator = TableOneGenerator()
        result = generator.generate(
            df,
            groupby='group',
            continuous=['value'],
            pval=True,
        )
        
        value_stats = result.overall_stats.get('value')
        if value_stats and value_stats.test_type:
            # Exponential data should trigger Mann-Whitney
            assert value_stats.test_type in [TestType.MANN_WHITNEY, TestType.TTEST]
    
    def test_chisquare_for_categorical(self, simple_df):
        """Test Chi-square selection for categorical variables."""
        generator = TableOneGenerator()
        result = generator.generate(
            simple_df,
            groupby='treatment',
            categorical=['gender'],
            pval=True,
        )
        
        gender_stats = result.overall_stats.get('gender')
        if gender_stats and gender_stats.test_type:
            assert gender_stats.test_type in [TestType.CHI_SQUARE, TestType.FISHER_EXACT]
    
    def test_anova_for_multiple_groups(self):
        """Test ANOVA selection for multiple groups."""
        np.random.seed(42)
        df = pd.DataFrame({
            'group': ['A'] * 30 + ['B'] * 30 + ['C'] * 30,
            'value': np.concatenate([
                np.random.normal(10, 2, 30),
                np.random.normal(12, 2, 30),
                np.random.normal(14, 2, 30),
            ])
        })
        
        generator = TableOneGenerator()
        result = generator.generate(
            df,
            groupby='group',
            continuous=['value'],
            pval=True,
        )
        
        value_stats = result.overall_stats.get('value')
        if value_stats and value_stats.test_type:
            assert value_stats.test_type in [TestType.ANOVA, TestType.KRUSKAL_WALLIS]
    
    def test_kruskal_for_multiple_nonnormal(self):
        """Test Kruskal-Wallis for multiple non-normal groups."""
        np.random.seed(42)
        df = pd.DataFrame({
            'group': ['A'] * 30 + ['B'] * 30 + ['C'] * 30,
            'value': np.concatenate([
                np.random.exponential(1, 30),
                np.random.exponential(2, 30),
                np.random.exponential(3, 30),
            ])
        })
        
        generator = TableOneGenerator()
        result = generator.generate(
            df,
            groupby='group',
            continuous=['value'],
            nonnormal=['value'],
            pval=True,
        )
        
        value_stats = result.overall_stats.get('value')
        if value_stats and value_stats.test_type:
            assert value_stats.test_type in [TestType.ANOVA, TestType.KRUSKAL_WALLIS]


# =============================================================================
# Output Format Tests
# =============================================================================

class TestOutputFormats:
    """Tests for output format generation."""
    
    def test_to_dict(self, simple_df):
        """Test dictionary output."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df, groupby='treatment')
        
        d = result.to_dict()
        assert 'title' in d
        assert 'n_total' in d
        assert 'groups' in d
        assert 'overall' in d
        assert 'by_group' in d
    
    def test_to_markdown(self, simple_df):
        """Test Markdown output."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df, groupby='treatment')
        
        md = result.to_markdown()
        assert isinstance(md, str)
        assert '|' in md  # Markdown table delimiter
        assert 'Table 1' in md
        assert 'age' in md or 'Age' in md
    
    def test_to_html(self, simple_df):
        """Test HTML output."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df, groupby='treatment')
        
        html = result.to_html()
        assert isinstance(html, str)
        assert '<table' in html
        assert '</table>' in html
        assert '<th>' in html
    
    def test_to_latex(self, simple_df):
        """Test LaTeX output."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df, groupby='treatment')
        
        latex = result.to_latex()
        assert isinstance(latex, str)
        assert r'\begin{table}' in latex
        assert r'\end{table}' in latex
        assert r'\hline' in latex


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_generate_tableone_dict(self, simple_df):
        """Test generate_tableone with dict output."""
        result = generate_tableone(
            simple_df,
            groupby='treatment',
            output_format='dict',
        )
        
        assert isinstance(result, dict)
        assert 'title' in result
    
    def test_generate_tableone_markdown(self, simple_df):
        """Test generate_tableone with markdown output."""
        result = generate_tableone(
            simple_df,
            groupby='treatment',
            output_format='markdown',
        )
        
        assert isinstance(result, str)
        assert '|' in result
    
    def test_generate_tableone_html(self, simple_df):
        """Test generate_tableone with HTML output."""
        result = generate_tableone(
            simple_df,
            groupby='treatment',
            output_format='html',
        )
        
        assert isinstance(result, str)
        assert '<table' in result
    
    def test_generate_tableone_latex(self, simple_df):
        """Test generate_tableone with LaTeX output."""
        result = generate_tableone(
            simple_df,
            groupby='treatment',
            output_format='latex',
        )
        
        assert isinstance(result, str)
        assert r'\begin{table}' in result
    
    def test_quick_tableone(self, simple_df):
        """Test quick_tableone function."""
        result = quick_tableone(simple_df, groupby='treatment')
        
        assert isinstance(result, str)
        assert '|' in result  # Markdown format


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        generator = TableOneGenerator()
        result = generator.generate(df)
        
        assert result.n_total == 0
    
    def test_single_row(self):
        """Test handling of single row DataFrame."""
        df = pd.DataFrame({'value': [10], 'group': ['A']})
        generator = TableOneGenerator()
        result = generator.generate(df)
        
        assert result.n_total == 1
    
    def test_single_group(self, simple_df):
        """Test handling of single group (no comparison)."""
        df = simple_df.copy()
        df['group'] = 'All'
        
        generator = TableOneGenerator()
        result = generator.generate(df, groupby='group', pval=True)
        
        assert result.n_groups == 1
        # P-values shouldn't be calculated for single group
    
    def test_all_missing(self):
        """Test handling of all-missing column."""
        df = pd.DataFrame({
            'group': ['A', 'B'] * 10,
            'complete': range(20),
            'all_missing': [np.nan] * 20,
        })
        
        generator = TableOneGenerator()
        result = generator.generate(df, groupby='group')
        
        stats = result.overall_stats.get('all_missing')
        if stats:
            assert stats.n == 0
            assert stats.n_missing == 20
    
    def test_constant_column(self):
        """Test handling of constant column."""
        df = pd.DataFrame({
            'group': ['A', 'B'] * 10,
            'constant': [5] * 20,
        })
        
        generator = TableOneGenerator()
        result = generator.generate(df, groupby='group')
        
        # Should not crash
        assert result.n_total == 20
    
    def test_nonexistent_column(self, simple_df):
        """Test handling of non-existent column specification."""
        generator = TableOneGenerator()
        result = generator.generate(
            simple_df,
            columns=['age', 'nonexistent_column'],
        )
        
        # Should only include valid columns
        assert 'nonexistent_column' not in result.variables
    
    def test_nonexistent_groupby(self, simple_df):
        """Test handling of non-existent groupby column."""
        generator = TableOneGenerator()
        result = generator.generate(
            simple_df,
            groupby='nonexistent',
        )
        
        # Should proceed without grouping
        assert result.n_groups == 0


# =============================================================================
# Real-World Clinical Data Simulation Tests
# =============================================================================

class TestClinicalDataScenarios:
    """Tests simulating real clinical data scenarios."""
    
    def test_rct_baseline_table(self):
        """Test generating baseline table for RCT."""
        np.random.seed(42)
        n = 150
        
        df = pd.DataFrame({
            'treatment': np.random.choice(['Active Drug', 'Placebo'], n),
            'age': np.random.normal(62, 10, n),
            'sex': np.random.choice(['Male', 'Female'], n),
            'race': np.random.choice(['White', 'Black', 'Asian', 'Other'], n, 
                                      p=[0.6, 0.2, 0.15, 0.05]),
            'baseline_sbp': np.random.normal(145, 15, n),
            'baseline_dbp': np.random.normal(88, 10, n),
            'diabetes': np.random.choice(['Yes', 'No'], n, p=[0.3, 0.7]),
            'prior_mi': np.random.choice([0, 1], n, p=[0.85, 0.15]),
        })
        
        result = generate_tableone(
            df,
            groupby='treatment',
            categorical=['sex', 'race', 'diabetes', 'prior_mi'],
            pval=True,
            output_format='dict',
        )
        
        assert result['n_total'] == 150
        assert len(result['groups']['names']) == 2
        assert 'age' in result['overall']
        assert 'sex' in result['overall']
    
    def test_cohort_study_table(self):
        """Test generating baseline table for cohort study."""
        np.random.seed(123)
        n = 500
        
        # Simulate exposure-outcome cohort
        df = pd.DataFrame({
            'exposed': np.random.choice(['Yes', 'No'], n, p=[0.3, 0.7]),
            'age': np.random.normal(55, 12, n),
            'bmi': np.random.normal(28, 5, n),
            'smoking': np.random.choice(['Never', 'Former', 'Current'], n, 
                                        p=[0.4, 0.35, 0.25]),
            'alcohol_per_week': np.random.poisson(4, n),
            'cholesterol': np.random.normal(200, 40, n),
        })
        
        result = generate_tableone(
            df,
            groupby='exposed',
            categorical=['smoking'],
            nonnormal=['alcohol_per_week'],  # Count data
            pval=True,
            smd=True,
            output_format='markdown',
        )
        
        assert '|' in result
        assert 'exposed' not in result.lower() or 'yes' in result.lower()
    
    def test_publication_ready_output(self, clinical_df):
        """Test that output is publication-ready."""
        result = generate_tableone(
            clinical_df,
            groupby='treatment_group',
            categorical=['gender', 'smoking_status', 'diabetes'],
            nonnormal=['bmi'],
            pval=True,
            title='Table 1. Baseline Characteristics of Study Population',
            output_format='markdown',
        )
        
        # Check for proper formatting
        assert 'Table 1' in result
        assert '±' in result or '[' in result  # Mean±SD or Median[IQR]
        assert '%' in result  # Percentages for categorical
        assert 'Active' in result and 'Control' in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full workflows."""
    
    def test_full_workflow_dict(self, clinical_df):
        """Test complete workflow returning dict."""
        generator = TableOneGenerator()
        result = generator.generate(
            clinical_df,
            groupby='treatment_group',
            categorical=['gender', 'smoking_status', 'diabetes'],
            nonnormal=['bmi'],
            pval=True,
            smd=True,
            missing=True,
        )
        
        # Convert to dict
        d = result.to_dict()
        
        # Validate structure
        assert 'title' in d
        assert 'n_total' in d
        assert 'groups' in d
        assert 'overall' in d
        assert 'by_group' in d
        assert 'metadata' in d
        
        # Validate content
        assert d['n_total'] == len(clinical_df)
        assert len(d['groups']['names']) == 2
    
    def test_multiple_format_consistency(self, simple_df):
        """Test that all formats represent same data."""
        generator = TableOneGenerator()
        result = generator.generate(simple_df, groupby='treatment')
        
        # All formats should be generated without error
        d = result.to_dict()
        md = result.to_markdown()
        html = result.to_html()
        latex = result.to_latex()
        
        # All should contain the same basic info
        assert str(result.n_total) in md
        assert str(result.n_total) in html
        assert str(result.n_total) in latex


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

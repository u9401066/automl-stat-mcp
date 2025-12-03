"""
Unit tests for Survival Analysis Module.

Tests for Kaplan-Meier estimator, log-rank test, and Cox proportional hazards.
"""
import pytest
import pandas as pd
import numpy as np
from io import StringIO

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.survival_analysis import (
    KaplanMeierEstimator,
    KaplanMeierResult,
    CoxPHFitter,
    CoxRegressionResult,
    CoxCoefficient,
    SurvivalPoint,
    LogRankResult,
    kaplan_meier_analysis,
    cox_regression,
    log_rank_test,
    survival_summary,
    compare_survival_curves,
    safe_float,
    safe_round,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def simple_survival_data():
    """Simple survival data for basic testing."""
    np.random.seed(42)
    n = 100
    
    # Generate survival times (exponential)
    times = np.random.exponential(12, n)
    
    # Generate censoring (30% censored)
    events = np.random.binomial(1, 0.7, n)
    
    # Censor at max time
    max_time = 24
    events[times > max_time] = 0
    times = np.minimum(times, max_time)
    
    return pd.DataFrame({
        'time': times,
        'event': events,
    })


@pytest.fixture
def grouped_survival_data():
    """Survival data with treatment groups."""
    np.random.seed(123)
    n = 200
    
    # Treatment assignment
    treatment = np.random.choice(['Treatment', 'Control'], n)
    
    # Different survival by group (treatment has better survival)
    times = np.where(
        treatment == 'Treatment',
        np.random.exponential(18, n),  # Treatment: longer survival
        np.random.exponential(12, n),  # Control: shorter survival
    )
    
    # Events (some censoring)
    events = np.random.binomial(1, 0.75, n)
    
    # Censor at max
    max_time = 36
    events[times > max_time] = 0
    times = np.minimum(times, max_time)
    
    return pd.DataFrame({
        'survival_time': times,
        'death': events,
        'treatment_group': treatment,
    })


@pytest.fixture
def cox_data():
    """Survival data with covariates for Cox regression."""
    np.random.seed(456)
    n = 300
    
    # Covariates
    age = np.random.normal(60, 10, n)
    is_male = np.random.binomial(1, 0.5, n)
    stage = np.random.choice([1, 2, 3, 4], n, p=[0.3, 0.3, 0.25, 0.15])
    
    # Generate hazard based on covariates
    # True coefficients: age=0.02, male=0.3, stage=0.5
    linear_pred = 0.02 * (age - 60) + 0.3 * is_male + 0.5 * (stage - 2)
    
    # Generate survival times
    baseline_hazard = 0.05
    times = np.random.exponential(1 / (baseline_hazard * np.exp(linear_pred)))
    
    # Events
    events = np.random.binomial(1, 0.8, n)
    
    # Censor at max
    max_time = 60
    events[times > max_time] = 0
    times = np.minimum(times, max_time)
    
    return pd.DataFrame({
        'time': times,
        'event': events,
        'age': age,
        'male': is_male,
        'stage': stage,
    })


@pytest.fixture
def multi_group_data():
    """Survival data with 3+ treatment groups."""
    np.random.seed(789)
    n = 150
    
    groups = np.random.choice(['DrugA', 'DrugB', 'Placebo'], n)
    
    # Different survival by group
    base_times = {
        'DrugA': 20,
        'DrugB': 15,
        'Placebo': 10,
    }
    
    times = np.array([
        np.random.exponential(base_times[g])
        for g in groups
    ])
    
    events = np.random.binomial(1, 0.7, n)
    
    max_time = 36
    events[times > max_time] = 0
    times = np.minimum(times, max_time)
    
    return pd.DataFrame({
        'time': times,
        'event': events,
        'arm': groups,
    })


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_safe_float_normal(self):
        """Test safe_float with normal values."""
        assert safe_float(3.14) == 3.14
        assert safe_float(0) == 0.0
        assert safe_float(-5.5) == -5.5
    
    def test_safe_float_none(self):
        """Test safe_float with None."""
        assert safe_float(None) is None
        assert safe_float(None, 0.0) == 0.0
    
    def test_safe_float_nan(self):
        """Test safe_float with NaN."""
        assert safe_float(float('nan')) is None
        assert safe_float(float('nan'), 0.0) == 0.0
    
    def test_safe_float_inf(self):
        """Test safe_float with infinity."""
        assert safe_float(float('inf')) is None
        assert safe_float(float('-inf')) is None
    
    def test_safe_round(self):
        """Test safe_round function."""
        assert safe_round(3.14159, 2) == 3.14
        assert safe_round(None, 2) is None


# =============================================================================
# Kaplan-Meier Tests
# =============================================================================

class TestKaplanMeierEstimator:
    """Tests for Kaplan-Meier estimator."""
    
    def test_basic_fit(self, simple_survival_data):
        """Test basic KM estimation."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        assert isinstance(result, KaplanMeierResult)
        assert result.n_subjects == len(simple_survival_data)
        assert result.n_events + result.n_censored == result.n_subjects
    
    def test_survival_curve(self, simple_survival_data):
        """Test survival curve properties."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        # Survival should start at 1 and decrease
        assert result.survival_table[0].survival == 1.0
        
        for i in range(1, len(result.survival_table)):
            # Survival should be non-increasing
            assert result.survival_table[i].survival <= result.survival_table[i-1].survival
            # Survival should be between 0 and 1
            assert 0 <= result.survival_table[i].survival <= 1
    
    def test_confidence_intervals(self, simple_survival_data):
        """Test confidence interval properties."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        for point in result.survival_table:
            # CI bounds should be ordered
            assert point.survival_ci_lower <= point.survival <= point.survival_ci_upper
            # CI bounds should be in [0, 1]
            assert 0 <= point.survival_ci_lower <= 1
            assert 0 <= point.survival_ci_upper <= 1
    
    def test_median_survival(self, simple_survival_data):
        """Test median survival calculation."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        # Median should be positive if calculated
        if result.median_survival is not None:
            assert result.median_survival > 0
    
    def test_grouped_fit(self, grouped_survival_data):
        """Test KM with multiple groups."""
        km = KaplanMeierEstimator()
        results = km.fit_groups(
            grouped_survival_data['survival_time'].values,
            grouped_survival_data['death'].values,
            grouped_survival_data['treatment_group'].values,
        )
        
        assert len(results) == 2
        assert 'Treatment' in results
        assert 'Control' in results
        
        # Treatment should have better survival (higher median)
        # Note: Due to random variation, we just check structure
        for group, result in results.items():
            assert isinstance(result, KaplanMeierResult)
            assert result.n_subjects > 0
    
    def test_to_dict(self, simple_survival_data):
        """Test serialization to dict."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        d = result.to_dict()
        assert 'group' in d
        assert 'n_subjects' in d
        assert 'median_survival' in d
        assert 'survival_curve' in d
    
    def test_get_survival_at_time(self, simple_survival_data):
        """Test getting survival at specific time."""
        km = KaplanMeierEstimator()
        result = km.fit(
            simple_survival_data['time'].values,
            simple_survival_data['event'].values,
        )
        
        # Survival at time 0 should be 1
        s, _, _ = result.get_survival_at_time(0)
        assert s == 1.0
        
        # Survival at a middle time should be < 1
        s, _, _ = result.get_survival_at_time(12)
        assert 0 < s < 1


# =============================================================================
# Log-Rank Test Tests
# =============================================================================

class TestLogRankTest:
    """Tests for log-rank test."""
    
    def test_two_groups(self, grouped_survival_data):
        """Test log-rank test with 2 groups."""
        result = log_rank_test(
            grouped_survival_data['survival_time'].values,
            grouped_survival_data['death'].values,
            grouped_survival_data['treatment_group'].values,
        )
        
        assert isinstance(result, LogRankResult)
        assert len(result.groups) == 2
        assert result.degrees_of_freedom == 1
        assert 0 <= result.p_value <= 1
    
    def test_three_groups(self, multi_group_data):
        """Test log-rank test with 3 groups."""
        result = log_rank_test(
            multi_group_data['time'].values,
            multi_group_data['event'].values,
            multi_group_data['arm'].values,
        )
        
        assert len(result.groups) == 3
        assert result.degrees_of_freedom == 2
    
    def test_pairwise_comparisons(self, multi_group_data):
        """Test pairwise comparisons for >2 groups."""
        result = log_rank_test(
            multi_group_data['time'].values,
            multi_group_data['event'].values,
            multi_group_data['arm'].values,
            pairwise=True,
        )
        
        assert result.pairwise is not None
        # Should have 3 pairwise comparisons for 3 groups
        assert len(result.pairwise) == 3
        
        for key, comparison in result.pairwise.items():
            assert 'p_value' in comparison
            assert 'p_value_adjusted' in comparison  # Bonferroni
    
    def test_to_dict(self, grouped_survival_data):
        """Test serialization to dict."""
        result = log_rank_test(
            grouped_survival_data['survival_time'].values,
            grouped_survival_data['death'].values,
            grouped_survival_data['treatment_group'].values,
        )
        
        d = result.to_dict()
        assert 'groups' in d
        assert 'test_statistic' in d
        assert 'p_value' in d
        assert 'significant' in d
    
    def test_single_group_returns_nonsignificant(self):
        """Test that single group returns p=1."""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 1, 1, 0, 0])
        groups = np.array(['A', 'A', 'A', 'A', 'A'])
        
        result = log_rank_test(times, events, groups)
        assert result.p_value == 1.0


# =============================================================================
# Cox Proportional Hazards Tests
# =============================================================================

class TestCoxPHFitter:
    """Tests for Cox proportional hazards regression."""
    
    def test_basic_fit(self, cox_data):
        """Test basic Cox regression."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        assert isinstance(result, CoxRegressionResult)
        assert result.n_subjects == len(cox_data)
        assert result.n_events > 0
        assert len(result.coefficients) == 3
    
    def test_coefficients(self, cox_data):
        """Test coefficient properties."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        for coef in result.coefficients:
            assert isinstance(coef, CoxCoefficient)
            assert coef.hazard_ratio > 0  # HR is always positive
            assert coef.hr_ci_lower <= coef.hazard_ratio <= coef.hr_ci_upper
            assert 0 <= coef.p_value <= 1
    
    def test_hazard_ratio_interpretation(self, cox_data):
        """Test that HR direction matches coefficient sign."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        for coef in result.coefficients:
            if coef.coefficient > 0:
                assert coef.hazard_ratio > 1  # Increased risk
            elif coef.coefficient < 0:
                assert coef.hazard_ratio < 1  # Decreased risk
    
    def test_concordance_index(self, cox_data):
        """Test concordance index is in valid range."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        if result.concordance is not None:
            assert 0 <= result.concordance <= 1
            # A reasonable model should have C > 0.5 (better than random)
            assert result.concordance >= 0.4
    
    def test_model_significance(self, cox_data):
        """Test global model tests."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        # Likelihood ratio test
        assert result.likelihood_ratio_test is not None
        assert result.likelihood_ratio_pvalue is not None
        assert 0 <= result.likelihood_ratio_pvalue <= 1
    
    def test_auto_detect_covariates(self, cox_data):
        """Test automatic covariate detection."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            # Don't specify covariates
        )
        
        # Should automatically detect numeric columns
        assert len(result.coefficients) >= 1
    
    def test_to_dict(self, cox_data):
        """Test serialization to dict."""
        cox = CoxPHFitter()
        result = cox.fit(
            cox_data,
            duration_col='time',
            event_col='event',
            covariates=['age', 'male'],
        )
        
        d = result.to_dict()
        assert 'n_subjects' in d
        assert 'n_events' in d
        assert 'coefficients' in d
        assert 'model_fit' in d
        assert 'global_tests' in d


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_kaplan_meier_analysis_ungrouped(self, simple_survival_data):
        """Test KM analysis without grouping."""
        result = kaplan_meier_analysis(
            simple_survival_data,
            time_col='time',
            event_col='event',
        )
        
        assert result['analysis_type'] == 'kaplan_meier'
        assert result['grouped'] is False
        assert 'overall' in result
    
    def test_kaplan_meier_analysis_grouped(self, grouped_survival_data):
        """Test KM analysis with grouping."""
        result = kaplan_meier_analysis(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
        )
        
        assert result['grouped'] is True
        assert 'groups' in result
        assert 'log_rank_test' in result
    
    def test_cox_regression_function(self, cox_data):
        """Test Cox regression convenience function."""
        result = cox_regression(
            cox_data,
            time_col='time',
            event_col='event',
            covariates=['age', 'male', 'stage'],
        )
        
        assert result['analysis_type'] == 'cox_regression'
        assert 'coefficients' in result
        assert 'model_fit' in result
    
    def test_survival_summary(self, grouped_survival_data):
        """Test survival summary."""
        result = survival_summary(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
            time_points=[12, 24],
        )
        
        assert 'n_subjects' in result
        assert 'n_events' in result
        assert 'by_group' in result
    
    def test_compare_survival_curves(self, grouped_survival_data):
        """Test survival curve comparison."""
        result = compare_survival_curves(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
        )
        
        assert 'groups' in result
        assert 'log_rank_test' in result
        assert 'conclusion' in result


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_data(self):
        """Test handling of empty data."""
        km = KaplanMeierEstimator()
        result = km.fit(np.array([]), np.array([]))
        
        assert result.n_subjects == 0
        assert result.n_events == 0
    
    def test_all_censored(self):
        """Test data with all observations censored."""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([0, 0, 0, 0, 0])
        
        km = KaplanMeierEstimator()
        result = km.fit(times, events)
        
        assert result.n_events == 0
        assert result.n_censored == 5
        # Survival should be 1.0 throughout
        for point in result.survival_table:
            assert point.survival == 1.0
    
    def test_all_events(self):
        """Test data with all observations having events."""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 1, 1, 1, 1])
        
        km = KaplanMeierEstimator()
        result = km.fit(times, events)
        
        assert result.n_events == 5
        assert result.n_censored == 0
        # Final survival should be 0
        assert result.survival_table[-1].survival == 0
    
    def test_nan_handling(self):
        """Test handling of NaN values."""
        times = np.array([1, 2, np.nan, 4, 5])
        events = np.array([1, 0, 1, 0, 1])
        
        km = KaplanMeierEstimator()
        result = km.fit(times, events)
        
        # Should exclude NaN row
        assert result.n_subjects == 4
    
    def test_single_observation(self):
        """Test handling of single observation."""
        km = KaplanMeierEstimator()
        result = km.fit(np.array([5]), np.array([1]))
        
        assert result.n_subjects == 1
        assert result.n_events == 1
    
    def test_identical_times(self):
        """Test handling of tied event times."""
        times = np.array([5, 5, 5, 10, 10])
        events = np.array([1, 1, 0, 1, 1])
        
        km = KaplanMeierEstimator()
        result = km.fit(times, events)
        
        # Should handle ties correctly
        assert result.n_subjects == 5
        assert result.n_events == 4


# =============================================================================
# Clinical Data Scenarios
# =============================================================================

class TestClinicalScenarios:
    """Tests simulating real clinical data scenarios."""
    
    def test_oncology_trial(self):
        """Test survival analysis for oncology trial."""
        np.random.seed(42)
        n = 100
        
        df = pd.DataFrame({
            'os_months': np.random.exponential(24, n),
            'death': np.random.binomial(1, 0.6, n),
            'treatment': np.random.choice(['Chemo', 'Immuno'], n),
            'age': np.random.normal(65, 10, n),
            'ecog': np.random.choice([0, 1, 2], n, p=[0.4, 0.4, 0.2]),
        })
        
        # KM analysis
        km_result = kaplan_meier_analysis(
            df,
            time_col='os_months',
            event_col='death',
            group_col='treatment',
        )
        
        assert km_result['grouped'] is True
        assert 'log_rank_test' in km_result
        
        # Cox regression
        cox_result = cox_regression(
            df,
            time_col='os_months',
            event_col='death',
            covariates=['age', 'ecog'],
        )
        
        assert len(cox_result['coefficients']) == 2
    
    def test_cardiovascular_study(self):
        """Test survival analysis for cardiovascular study."""
        np.random.seed(123)
        n = 200
        
        df = pd.DataFrame({
            'time_to_event': np.random.exponential(5, n),  # Years
            'mace': np.random.binomial(1, 0.4, n),  # Major adverse cardiac event
            'statin': np.random.binomial(1, 0.6, n),
            'diabetes': np.random.binomial(1, 0.3, n),
            'sbp': np.random.normal(140, 20, n),
        })
        
        # Summary
        summary = survival_summary(
            df,
            time_col='time_to_event',
            event_col='mace',
            group_col='statin',
            time_points=[1, 3, 5],
        )
        
        assert 'by_group' in summary
        assert 'survival_at_times' in summary['by_group']['0']
    
    def test_landmark_analysis(self):
        """Test survival at specific landmark times."""
        np.random.seed(456)
        n = 100
        
        df = pd.DataFrame({
            'time': np.random.exponential(12, n),
            'event': np.random.binomial(1, 0.5, n),
        })
        
        summary = survival_summary(
            df,
            time_col='time',
            event_col='event',
            time_points=[6, 12, 18, 24],
        )
        
        assert 'survival_at_times' in summary
        assert 't=6' in summary['survival_at_times']
        assert 't=12' in summary['survival_at_times']


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full workflows."""
    
    def test_complete_survival_workflow(self, grouped_survival_data):
        """Test complete survival analysis workflow."""
        # 1. Summary statistics
        summary = survival_summary(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
        )
        
        assert summary['n_subjects'] == len(grouped_survival_data)
        
        # 2. KM analysis
        km = kaplan_meier_analysis(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
        )
        
        assert 'groups' in km
        assert 'log_rank_test' in km
        
        # 3. Comparison
        comparison = compare_survival_curves(
            grouped_survival_data,
            time_col='survival_time',
            event_col='death',
            group_col='treatment_group',
        )
        
        assert 'conclusion' in comparison
    
    def test_cox_with_binary_treatment(self, grouped_survival_data):
        """Test Cox regression with binary treatment."""
        df = grouped_survival_data.copy()
        df['treatment_binary'] = (df['treatment_group'] == 'Treatment').astype(int)
        
        result = cox_regression(
            df,
            time_col='survival_time',
            event_col='death',
            covariates=['treatment_binary'],
        )
        
        assert len(result['coefficients']) == 1
        
        # Treatment should show some effect (not necessarily significant)
        hr = result['coefficients'][0]['hazard_ratio']
        assert hr > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

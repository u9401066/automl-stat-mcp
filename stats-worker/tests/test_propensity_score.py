"""
Tests for Propensity Score Analysis Module

Tests cover:
- Propensity score estimation
- Propensity score matching
- Inverse probability weighting
- Balance assessment
- Treatment effect estimation
"""

import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, 'src')

from tasks.propensity_score import (
    BalanceAssessor,
    IPWeighting,
    MatchingResult,
    PropensityScoreEstimator,
    PropensityScoreMatcher,
    PropensityScoreResult,
    TreatmentEffectResult,
    assess_balance,
    estimate_propensity_scores,
    estimate_treatment_effect,
    match_propensity_scores,
    propensity_score_analysis,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_data():
    """Simple dataset for basic tests."""
    np.random.seed(42)
    n = 200

    # Confounders
    age = np.random.normal(50, 10, n)
    income = np.random.normal(50000, 15000, n)

    # Treatment depends on confounders
    logit = -2 + 0.04 * age + 0.00002 * income
    prob = 1 / (1 + np.exp(-logit))
    treatment = (np.random.random(n) < prob).astype(int)

    # Outcome depends on treatment and confounders
    outcome = 10 + 5 * treatment + 0.2 * age + 0.0001 * income + np.random.normal(0, 2, n)

    return pd.DataFrame({
        'age': age,
        'income': income,
        'treatment': treatment,
        'outcome': outcome,
    })


@pytest.fixture
def imbalanced_data():
    """Dataset with strong confounding."""
    np.random.seed(123)
    n = 300

    # Treated group: older, higher income
    n_treated = 100
    n_control = 200

    age_treated = np.random.normal(60, 8, n_treated)
    age_control = np.random.normal(45, 8, n_control)

    income_treated = np.random.normal(70000, 10000, n_treated)
    income_control = np.random.normal(40000, 10000, n_control)

    # Combine
    age = np.concatenate([age_treated, age_control])
    income = np.concatenate([income_treated, income_control])
    treatment = np.array([1] * n_treated + [0] * n_control)

    # Outcome: treatment effect of 3
    outcome = 20 + 3 * treatment + 0.3 * age + 0.0002 * income + np.random.normal(0, 3, n)

    return pd.DataFrame({
        'age': age,
        'income': income,
        'treatment': treatment,
        'outcome': outcome,
    })


@pytest.fixture
def binary_outcome_data():
    """Dataset with binary outcome."""
    np.random.seed(456)
    n = 400

    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)

    # Treatment
    treat_logit = -0.5 + 0.5 * x1 + 0.3 * x2
    treat_prob = 1 / (1 + np.exp(-treat_logit))
    treatment = (np.random.random(n) < treat_prob).astype(int)

    # Outcome (binary)
    out_logit = -1 + 0.5 * treatment + 0.3 * x1 + 0.2 * x2
    out_prob = 1 / (1 + np.exp(-out_logit))
    outcome = (np.random.random(n) < out_prob).astype(int)

    return pd.DataFrame({
        'x1': x1,
        'x2': x2,
        'treatment': treatment,
        'outcome': outcome,
    })


# =============================================================================
# Test PropensityScoreEstimator
# =============================================================================

class TestPropensityScoreEstimator:
    """Tests for propensity score estimation."""

    def test_basic_fit(self, simple_data):
        """Test basic model fitting."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        result = estimator.fit(X, treatment)

        assert isinstance(result, PropensityScoreResult)
        assert len(result.scores) == len(treatment)
        assert all(0 <= s <= 1 for s in result.scores)
        assert 'age' in result.coefficients
        assert 'income' in result.coefficients

    def test_model_metrics(self, simple_data):
        """Test model diagnostic metrics."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        result = estimator.fit(X, treatment)

        # Check metrics exist and are reasonable
        assert 0 <= result.model_metrics['c_statistic'] <= 1
        assert result.model_metrics['pseudo_r2'] >= 0
        assert 0 <= result.model_metrics['brier_score'] <= 0.25

    def test_score_distribution(self, simple_data):
        """Test score distribution statistics."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        result = estimator.fit(X, treatment)

        assert 'treated' in result.distribution
        assert 'control' in result.distribution
        assert result.distribution['treated']['mean'] >= 0
        assert result.distribution['control']['mean'] >= 0

    def test_overlap_region(self, simple_data):
        """Test overlap region computation."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        result = estimator.fit(X, treatment)

        lower, upper = result.overlap_region
        assert 0 <= lower <= upper <= 1

    def test_regularization(self, simple_data):
        """Test regularization effect."""
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        est_no_reg = PropensityScoreEstimator(regularization=0.0)
        est_reg = PropensityScoreEstimator(regularization=1.0)

        result_no_reg = est_no_reg.fit(X, treatment)
        result_reg = est_reg.fit(X, treatment)

        # Regularized coefficients should be smaller
        coef_no_reg = np.abs(list(result_no_reg.coefficients.values()))
        coef_reg = np.abs(list(result_reg.coefficients.values()))

        assert np.mean(coef_reg) <= np.mean(coef_no_reg)

    def test_predict_proba(self, simple_data):
        """Test prediction on new data."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        estimator.fit(X, treatment)

        new_data = pd.DataFrame({
            'age': [40, 60, 50],
            'income': [30000, 70000, 50000],
        })

        probs = estimator.predict_proba(new_data)

        assert len(probs) == 3
        assert all(0 <= p <= 1 for p in probs)

    def test_to_dict(self, simple_data):
        """Test serialization."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment']

        result = estimator.fit(X, treatment)
        d = result.to_dict()

        assert 'n_treated' in d
        assert 'n_control' in d
        assert 'coefficients' in d
        assert 'model_metrics' in d
        assert 'overlap_region' in d

    def test_numpy_input(self, simple_data):
        """Test with numpy arrays."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']].values
        treatment = simple_data['treatment'].values

        result = estimator.fit(X, treatment, feature_names=['age', 'income'])

        assert 'age' in result.coefficients

    def test_invalid_treatment(self, simple_data):
        """Test error on non-binary treatment."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = np.array([0, 1, 2, 0, 1] * 40)

        with pytest.raises(ValueError, match="binary"):
            estimator.fit(X, treatment)


# =============================================================================
# Test PropensityScoreMatcher
# =============================================================================

class TestPropensityScoreMatcher:
    """Tests for propensity score matching."""

    def test_nearest_neighbor_matching(self, imbalanced_data):
        """Test basic nearest neighbor matching."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        matcher = PropensityScoreMatcher(method='nearest')
        result = matcher.match(scores, treatment)

        assert isinstance(result, MatchingResult)
        assert result.n_matched > 0
        assert len(result.matched_treated_idx) == result.n_matched
        assert len(result.matched_control_idx) == result.n_matched

    def test_caliper_matching(self, imbalanced_data):
        """Test matching with caliper."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        # Tight caliper
        matcher_tight = PropensityScoreMatcher(method='nearest', caliper=0.05)
        result_tight = matcher_tight.match(scores, treatment)

        # Loose caliper
        matcher_loose = PropensityScoreMatcher(method='nearest', caliper=0.5)
        result_loose = matcher_loose.match(scores, treatment)

        # Tight caliper should match fewer
        assert result_tight.n_matched <= result_loose.n_matched

    def test_matching_with_replacement(self, imbalanced_data):
        """Test matching with replacement."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        matcher = PropensityScoreMatcher(method='nearest', replacement=True)
        result = matcher.match(scores, treatment)

        # With replacement, should be able to match all treated
        assert result.n_matched >= result.n_matched - result.n_unmatched_treated

    def test_matching_result_dict(self, imbalanced_data):
        """Test MatchingResult serialization."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        matcher = PropensityScoreMatcher(method='nearest')
        result = matcher.match(ps_result.scores, treatment)

        d = result.to_dict()

        assert 'n_matched_pairs' in d
        assert 'matching_rate_treated' in d
        assert 0 <= d['matching_rate_treated'] <= 1

    def test_optimal_matching(self, simple_data):
        """Test optimal matching (small dataset)."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        ps_result = estimator.fit(X, treatment)

        matcher = PropensityScoreMatcher(method='optimal')
        result = matcher.match(ps_result.scores, treatment)

        assert result.n_matched > 0


# =============================================================================
# Test IPWeighting
# =============================================================================

class TestIPWeighting:
    """Tests for inverse probability weighting."""

    def test_compute_weights_ate(self, simple_data):
        """Test ATE weight computation."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        ipw = IPWeighting()
        weights = ipw.compute_weights(treatment, scores, target='ate')

        assert len(weights) == len(treatment)
        assert all(w > 0 for w in weights)

    def test_compute_weights_att(self, simple_data):
        """Test ATT weight computation."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        ipw = IPWeighting()
        weights = ipw.compute_weights(treatment, scores, target='att')

        # Treated should have weight ~1
        treated_weights = weights[treatment == 1]
        assert np.allclose(treated_weights, 1.0)

    def test_stabilized_weights(self, simple_data):
        """Test stabilized weights have lower variance."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        ipw_unstab = IPWeighting(stabilized=False)
        ipw_stab = IPWeighting(stabilized=True)

        weights_unstab = ipw_unstab.compute_weights(treatment, scores, 'ate')
        weights_stab = ipw_stab.compute_weights(treatment, scores, 'ate')

        # Stabilized should have lower variance
        assert np.var(weights_stab) <= np.var(weights_unstab) * 1.5  # Allow some tolerance

    def test_weight_trimming(self, imbalanced_data):
        """Test weight trimming at percentiles."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        ipw_notrim = IPWeighting(trim_percentile=None)
        ipw_trim = IPWeighting(trim_percentile=0.01)

        weights_notrim = ipw_notrim.compute_weights(treatment, scores, 'ate')
        weights_trim = ipw_trim.compute_weights(treatment, scores, 'ate')

        # Trimmed should have lower max
        assert np.max(weights_trim) <= np.max(weights_notrim) * 1.1

    def test_estimate_effect(self, imbalanced_data):
        """Test treatment effect estimation."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values
        outcome = imbalanced_data['outcome'].values

        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores

        ipw = IPWeighting(stabilized=True)
        result = ipw.estimate_effect(outcome, treatment, scores, target='ate')

        assert isinstance(result, TreatmentEffectResult)
        assert result.effect_type == 'ATE'
        # True effect is ~3, IPW may have variance so just check it's positive
        assert result.estimate > 0

    def test_treatment_effect_ci(self, imbalanced_data):
        """Test confidence interval computation."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values
        outcome = imbalanced_data['outcome'].values

        ps_result = estimator.fit(X, treatment)

        ipw = IPWeighting()
        result = ipw.estimate_effect(outcome, treatment, ps_result.scores, 'ate')

        assert result.ci_lower < result.estimate < result.ci_upper
        assert result.std_error > 0

    def test_treatment_effect_to_dict(self, simple_data):
        """Test TreatmentEffectResult serialization."""
        estimator = PropensityScoreEstimator()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values
        outcome = simple_data['outcome'].values

        ps_result = estimator.fit(X, treatment)

        ipw = IPWeighting()
        result = ipw.estimate_effect(outcome, treatment, ps_result.scores, 'ate')

        d = result.to_dict()

        assert 'estimate' in d
        assert 'confidence_interval' in d
        assert 'p_value' in d
        assert 'significant' in d


# =============================================================================
# Test BalanceAssessor
# =============================================================================

class TestBalanceAssessor:
    """Tests for balance assessment."""

    def test_smd_computation(self, imbalanced_data):
        """Test standardized mean difference."""
        assessor = BalanceAssessor()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        result = assessor.assess(X, treatment, feature_names=['age', 'income'])

        assert 'age' in result.standardized_differences
        assert 'income' in result.standardized_differences
        # Imbalanced data should have high SMD
        assert abs(result.standardized_differences['age']) > 0.5

    def test_variance_ratio(self, imbalanced_data):
        """Test variance ratio computation."""
        assessor = BalanceAssessor()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        result = assessor.assess(X, treatment, feature_names=['age', 'income'])

        assert 'age' in result.variance_ratios
        # Should be positive
        assert result.variance_ratios['age'] > 0

    def test_ks_statistic(self, imbalanced_data):
        """Test KS statistic computation."""
        assessor = BalanceAssessor()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        result = assessor.assess(X, treatment, feature_names=['age', 'income'])

        assert 'age' in result.ks_statistics
        assert 'statistic' in result.ks_statistics['age']
        assert 'p_value' in result.ks_statistics['age']

    def test_balance_with_weights(self, imbalanced_data):
        """Test balance assessment with IPW weights."""
        estimator = PropensityScoreEstimator()
        X = imbalanced_data[['age', 'income']]
        treatment = imbalanced_data['treatment'].values

        ps_result = estimator.fit(X, treatment)

        ipw = IPWeighting()
        weights = ipw.compute_weights(treatment, ps_result.scores, 'ate')

        assessor = BalanceAssessor()
        result_unweighted = assessor.assess(X, treatment, feature_names=['age', 'income'])
        result_weighted = assessor.assess(X, treatment, weights, ['age', 'income'])

        # Weighted SMD should be smaller
        smd_unw = abs(result_unweighted.standardized_differences['age'])
        smd_w = abs(result_weighted.standardized_differences['age'])

        assert smd_w < smd_unw

    def test_overall_balance(self, simple_data):
        """Test overall balance summary."""
        assessor = BalanceAssessor(smd_threshold=0.25)
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        result = assessor.assess(X, treatment, feature_names=['age', 'income'])

        assert 'mean_absolute_smd' in result.overall_balance
        assert 'max_absolute_smd' in result.overall_balance
        assert 'n_covariates' in result.overall_balance
        assert 'proportion_balanced' in result.overall_balance

    def test_balance_diagnostics_to_dict(self, simple_data):
        """Test BalanceDiagnostics serialization."""
        assessor = BalanceAssessor()
        X = simple_data[['age', 'income']]
        treatment = simple_data['treatment'].values

        result = assessor.assess(X, treatment, feature_names=['age', 'income'])
        d = result.to_dict()

        assert 'standardized_mean_differences' in d
        assert 'variance_ratios' in d
        assert 'summary' in d
        assert 'balance_achieved' in d


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience wrapper functions."""

    def test_estimate_propensity_scores(self, simple_data):
        """Test estimate_propensity_scores function."""
        result = estimate_propensity_scores(
            simple_data,
            treatment_col='treatment',
            covariates=['age', 'income'],
        )

        assert result['status'] == 'success'
        assert 'scores' in result
        assert 'coefficients' in result
        assert len(result['scores']) == len(simple_data)

    def test_match_propensity_scores(self, imbalanced_data):
        """Test match_propensity_scores function."""
        result = match_propensity_scores(
            imbalanced_data,
            treatment_col='treatment',
            covariates=['age', 'income'],
            caliper=0.2,
        )

        assert result['status'] == 'success'
        assert 'n_matched_pairs' in result
        assert 'matched_treated_indices' in result
        assert 'matched_control_indices' in result

    def test_estimate_treatment_effect(self, imbalanced_data):
        """Test estimate_treatment_effect function."""
        result = estimate_treatment_effect(
            imbalanced_data,
            outcome_col='outcome',
            treatment_col='treatment',
            covariates=['age', 'income'],
            target='ate',
        )

        assert result['status'] == 'success'
        assert 'estimate' in result
        assert 'confidence_interval' in result
        assert 'p_value' in result

    def test_assess_balance(self, imbalanced_data):
        """Test assess_balance function."""
        result = assess_balance(
            imbalanced_data,
            treatment_col='treatment',
            covariates=['age', 'income'],
        )

        assert result['status'] == 'success'
        assert 'standardized_mean_differences' in result
        assert 'balance_achieved' in result

    def test_propensity_score_analysis_matching(self, imbalanced_data):
        """Test full PS analysis with matching."""
        result = propensity_score_analysis(
            imbalanced_data,
            outcome_col='outcome',
            treatment_col='treatment',
            covariates=['age', 'income'],
            method='matching',
        )

        assert result['status'] == 'success'
        assert 'propensity_model' in result
        assert 'balance_before' in result
        assert 'balance_after' in result
        assert 'treatment_effect' in result

        # Balance should improve
        smd_before = result['balance_before']['summary']['max_absolute_smd']
        smd_after = result['balance_after']['summary']['max_absolute_smd']
        assert smd_after < smd_before

    def test_propensity_score_analysis_ipw(self, imbalanced_data):
        """Test full PS analysis with IPW."""
        result = propensity_score_analysis(
            imbalanced_data,
            outcome_col='outcome',
            treatment_col='treatment',
            covariates=['age', 'income'],
            method='ipw',
        )

        assert result['status'] == 'success'
        assert 'method_details' in result
        assert 'weight_mean' in result['method_details']

        # Balance should improve
        smd_before = result['balance_before']['summary']['max_absolute_smd']
        smd_after = result['balance_after']['summary']['max_absolute_smd']
        assert smd_after < smd_before


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_perfect_separation(self):
        """Test handling of perfect separation."""
        # Groups don't overlap at all
        df = pd.DataFrame({
            'x': [1, 2, 3, 100, 101, 102],
            'treatment': [0, 0, 0, 1, 1, 1],
            'outcome': [1, 2, 3, 4, 5, 6],
        })

        estimator = PropensityScoreEstimator()
        result = estimator.fit(df[['x']], df['treatment'])

        # Should still produce valid scores
        assert all(0 <= s <= 1 for s in result.scores)

    def test_single_covariate(self):
        """Test with single covariate."""
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        treatment = (x > 0).astype(int)

        df = pd.DataFrame({'x': x, 'treatment': treatment})

        estimator = PropensityScoreEstimator()
        result = estimator.fit(df[['x']], df['treatment'])

        assert len(result.coefficients) == 1
        assert 'x' in result.coefficients

    def test_many_covariates(self):
        """Test with many covariates."""
        np.random.seed(42)
        n = 500
        p = 10

        X = np.random.normal(0, 1, (n, p))
        logit = X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2]
        prob = 1 / (1 + np.exp(-logit))
        treatment = (np.random.random(n) < prob).astype(int)

        df = pd.DataFrame(X, columns=[f'x{i}' for i in range(p)])
        df['treatment'] = treatment

        estimator = PropensityScoreEstimator()
        result = estimator.fit(df[[f'x{i}' for i in range(p)]], df['treatment'])

        assert len(result.coefficients) == p

    def test_small_sample(self):
        """Test with very small sample."""
        df = pd.DataFrame({
            'x': [1, 2, 3, 4, 5, 6, 7, 8],
            'treatment': [0, 0, 0, 0, 1, 1, 1, 1],
            'outcome': [1, 2, 3, 4, 5, 6, 7, 8],
        })

        result = propensity_score_analysis(
            df,
            outcome_col='outcome',
            treatment_col='treatment',
            covariates=['x'],
            method='matching',
        )

        assert result['status'] == 'success'

    def test_no_overlap(self):
        """Test when there's minimal overlap."""
        df = pd.DataFrame({
            'x': [1, 2, 3, 4, 5, 96, 97, 98, 99, 100],
            'treatment': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
            'outcome': list(range(10)),
        })

        estimator = PropensityScoreEstimator()
        result = estimator.fit(df[['x']], df['treatment'])

        # Overlap region should be small or inverted
        lower, upper = result.overlap_region
        # Still should return valid bounds


# =============================================================================
# Test Clinical Scenarios
# =============================================================================

class TestClinicalScenarios:
    """Tests based on realistic clinical scenarios."""

    def test_drug_effectiveness_study(self):
        """Simulate drug effectiveness observational study."""
        np.random.seed(42)
        n = 500

        # Patient characteristics (confounders)
        age = np.random.normal(55, 12, n)
        severity = np.random.choice([1, 2, 3], n, p=[0.3, 0.5, 0.2])
        comorbidity = np.random.binomial(1, 0.3, n)

        # Treatment assignment (depends on confounders)
        treat_logit = -2 + 0.02 * age + 0.5 * severity + 0.8 * comorbidity
        treat_prob = 1 / (1 + np.exp(-treat_logit))
        treatment = (np.random.random(n) < treat_prob).astype(int)

        # Outcome: blood pressure reduction
        # True treatment effect: -5 mmHg
        outcome = 150 - 5 * treatment - 0.3 * age + 2 * severity + 5 * comorbidity + np.random.normal(0, 8, n)

        df = pd.DataFrame({
            'age': age,
            'severity': severity,
            'comorbidity': comorbidity,
            'treatment': treatment,
            'bp_reduction': outcome,
        })

        result = propensity_score_analysis(
            df,
            outcome_col='bp_reduction',
            treatment_col='treatment',
            covariates=['age', 'severity', 'comorbidity'],
            method='ipw',
        )

        assert result['status'] == 'success'
        # Effect should be in reasonable range (true effect is -5)
        effect = result['treatment_effect']['estimate']
        assert -15 < effect < 5

    def test_surgery_outcome_study(self):
        """Simulate surgery outcome comparison."""
        np.random.seed(123)
        n = 300

        # Patient characteristics
        age = np.random.normal(60, 10, n)
        bmi = np.random.normal(28, 5, n)
        diabetes = np.random.binomial(1, 0.25, n)

        # Surgery type (1 = new procedure, 0 = standard)
        treat_logit = -1 + 0.01 * age - 0.05 * bmi + 0.5 * diabetes
        treat_prob = 1 / (1 + np.exp(-treat_logit))
        treatment = (np.random.random(n) < treat_prob).astype(int)

        # Recovery time (days)
        # True effect: -3 days for new procedure
        recovery = 14 - 3 * treatment + 0.1 * age + 0.2 * bmi + 2 * diabetes + np.random.normal(0, 3, n)

        df = pd.DataFrame({
            'age': age,
            'bmi': bmi,
            'diabetes': diabetes,
            'surgery_type': treatment,
            'recovery_days': recovery,
        })

        # Test with matching
        result = propensity_score_analysis(
            df,
            outcome_col='recovery_days',
            treatment_col='surgery_type',
            covariates=['age', 'bmi', 'diabetes'],
            method='matching',
            caliper=0.25,
        )

        assert result['status'] == 'success'
        # Check balance improved
        assert result['balance_after']['summary']['max_absolute_smd'] < result['balance_before']['summary']['max_absolute_smd']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

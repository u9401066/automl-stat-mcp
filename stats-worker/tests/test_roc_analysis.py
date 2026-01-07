"""
Unit Tests for ROC/AUC Analysis Module

Tests cover the main convenience functions:
- compute_roc_curve
- compare_roc_curves (DeLong test)
- find_optimal_threshold
- analyze_calibration
- compute_precision_recall
- full_classifier_evaluation
"""

import os
import sys

import numpy as np
import pytest
from scipy.special import expit  # logistic function

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tasks.roc_analysis import (
    analyze_calibration,
    compare_multiple_models,
    compare_roc_curves,
    compute_precision_recall,
    compute_roc_curve,
    find_optimal_threshold,
    full_classifier_evaluation,
    generate_publication_report,
    threshold_analysis,
)

# ==================== Fixtures ====================

@pytest.fixture
def binary_classification_data():
    """Generate binary classification test data."""
    np.random.seed(42)
    n = 500

    # True labels
    y_true = np.random.binomial(1, 0.3, n)  # 30% positive

    # Good model scores (correlated with truth)
    noise = np.random.normal(0, 0.5, n)
    y_score_good = expit(1.5 * y_true + noise - 0.5)

    # Poor model scores (weakly correlated)
    noise2 = np.random.normal(0, 1.5, n)
    y_score_poor = expit(0.3 * y_true + noise2 - 0.3)

    # Random model (no discrimination)
    y_score_random = np.random.uniform(0, 1, n)

    return {
        'y_true': y_true,
        'y_score_good': y_score_good,
        'y_score_poor': y_score_poor,
        'y_score_random': y_score_random,
        'n_positive': y_true.sum(),
        'n_negative': n - y_true.sum(),
    }


@pytest.fixture
def perfect_classifier_data():
    """Generate perfectly separable data."""
    y_true = np.array([0]*100 + [1]*100)
    y_score = np.array([0.1]*100 + [0.9]*100)  # Perfect separation
    return {'y_true': y_true, 'y_score': y_score}


@pytest.fixture
def calibrated_model_data():
    """Generate well-calibrated predictions."""
    np.random.seed(123)
    n = 1000

    # Well-calibrated: predicted probs match actual frequencies
    y_score = np.random.uniform(0, 1, n)
    y_true = (np.random.uniform(0, 1, n) < y_score).astype(int)

    return {'y_true': y_true, 'y_score': y_score}


# ==================== ROC Curve Tests ====================

class TestComputeROCCurve:
    """Tests for compute_roc_curve function."""

    def test_basic_roc(self, binary_classification_data):
        """Test basic ROC curve computation."""
        result = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert result['status'] == 'success'
        assert 'auc' in result
        assert 0 <= result['auc'] <= 1
        assert 'auc_ci' in result
        assert result['auc_ci']['lower'] <= result['auc'] <= result['auc_ci']['upper']

    def test_perfect_classifier(self, perfect_classifier_data):
        """Test ROC for perfect classifier."""
        result = compute_roc_curve(
            perfect_classifier_data['y_true'],
            perfect_classifier_data['y_score']
        )

        # Perfect classifier should have AUC = 1.0
        assert result['auc'] == pytest.approx(1.0, abs=0.01)

    def test_random_classifier(self, binary_classification_data):
        """Test ROC for random classifier."""
        result = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_random']
        )

        # Random classifier should have AUC ≈ 0.5
        assert 0.4 < result['auc'] < 0.6

    def test_good_vs_poor_model(self, binary_classification_data):
        """Test that good model has higher AUC than poor model."""
        result_good = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )
        result_poor = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_poor']
        )

        assert result_good['auc'] > result_poor['auc']

    def test_confidence_interval(self, binary_classification_data):
        """Test that CI is properly computed."""
        result = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        # CI should be valid
        assert result['auc_ci']['lower'] < result['auc_ci']['upper']
        assert result['auc_ci']['lower'] >= 0
        assert result['auc_ci']['upper'] <= 1

    def test_optimal_threshold(self, binary_classification_data):
        """Test optimal threshold is included."""
        result = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert 'optimal_threshold' in result
        assert 0 <= result['optimal_threshold'] <= 1

    def test_curve_points(self, binary_classification_data):
        """Test ROC curve points are included."""
        result = compute_roc_curve(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert 'curve' in result
        assert len(result['curve']) > 0


# ==================== DeLong Test Tests ====================

class TestDeLongComparison:
    """Tests for DeLong AUC comparison."""

    def test_compare_same_model(self, binary_classification_data):
        """Comparing model to itself should give p ≈ 1."""
        result = compare_roc_curves(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_good'],
        )

        assert result['comparison']['difference'] == pytest.approx(0, abs=0.001)
        assert result['comparison']['p_value'] > 0.99

    def test_compare_different_models(self, binary_classification_data):
        """Comparing good vs poor model should show difference."""
        result = compare_roc_curves(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_poor'],
            'Good Model',
            'Poor Model',
        )

        assert result['model1']['auc'] > result['model2']['auc']
        assert result['comparison']['difference'] > 0

    def test_compare_good_vs_random(self, binary_classification_data):
        """Good model vs random should be highly significant."""
        result = compare_roc_curves(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_random'],
        )

        # Should be statistically significant
        assert result['comparison']['p_value'] < 0.05
        assert result['comparison']['significant']

    def test_ci_for_difference(self, binary_classification_data):
        """Test confidence interval for AUC difference."""
        result = compare_roc_curves(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_poor'],
        )

        # CI should contain the difference
        ci = result['comparison']
        ci_diff = ci['ci_difference']
        assert ci_diff['lower'] <= ci['difference'] <= ci_diff['upper']

    def test_conclusion_text(self, binary_classification_data):
        """Test that conclusion text is generated."""
        result = compare_roc_curves(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_poor'],
            'Good Model',
            'Poor Model',
        )

        assert 'conclusion' in result
        assert 'Good Model' in result['conclusion']


# ==================== Calibration Tests ====================

class TestCalibrationAnalysis:
    """Tests for calibration analysis."""

    def test_basic_calibration(self, binary_classification_data):
        """Test basic calibration metrics."""
        result = analyze_calibration(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert result['status'] == 'success'
        assert 'brier_score' in result
        assert 0 <= result['brier_score'] <= 1

    def test_hosmer_lemeshow(self, calibrated_model_data):
        """Test Hosmer-Lemeshow test."""
        result = analyze_calibration(
            calibrated_model_data['y_true'],
            calibrated_model_data['y_score']
        )

        assert 'hosmer_lemeshow' in result
        assert 'statistic' in result['hosmer_lemeshow']
        assert 'p_value' in result['hosmer_lemeshow']

    def test_well_calibrated_flag(self, calibrated_model_data):
        """Test well_calibrated flag."""
        result = analyze_calibration(
            calibrated_model_data['y_true'],
            calibrated_model_data['y_score']
        )

        assert 'well_calibrated' in result

    def test_calibration_bins(self, binary_classification_data):
        """Test calibration bins data."""
        result = analyze_calibration(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            n_bins=5
        )

        assert 'bins' in result


# ==================== Precision-Recall Tests ====================

class TestPrecisionRecall:
    """Tests for precision-recall analysis."""

    def test_basic_pr_curve(self, binary_classification_data):
        """Test basic PR curve computation."""
        result = compute_precision_recall(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert result['status'] == 'success'
        assert 'auc_pr' in result
        assert 0 <= result['auc_pr'] <= 1
        assert 'average_precision' in result

    def test_perfect_classifier_pr(self, perfect_classifier_data):
        """Test PR curve for perfect classifier."""
        result = compute_precision_recall(
            perfect_classifier_data['y_true'],
            perfect_classifier_data['y_score']
        )

        # Perfect classifier should have AP close to 1
        assert result['average_precision'] > 0.95

    def test_imbalanced_data(self):
        """Test PR curve on imbalanced data."""
        np.random.seed(789)
        n = 1000
        # Highly imbalanced: 5% positive
        y_true = np.random.binomial(1, 0.05, n)
        y_score = expit(1.5 * y_true + np.random.normal(0, 0.5, n) - 0.5)

        result = compute_precision_recall(y_true, y_score)

        # PR-AUC should be reasonable for imbalanced data
        assert 0 < result['auc_pr'] <= 1


# ==================== Optimal Threshold Tests ====================

class TestOptimalThreshold:
    """Tests for optimal threshold selection."""

    def test_youden_method(self, binary_classification_data):
        """Test Youden method threshold selection."""
        result = find_optimal_threshold(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            method='youden'
        )

        assert result['status'] == 'success'
        assert 'threshold' in result
        assert 0 <= result['threshold'] <= 1
        assert 'sensitivity' in result
        assert 'specificity' in result

    def test_f1_method(self, binary_classification_data):
        """Test F1 score maximization."""
        result = find_optimal_threshold(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            method='f1'
        )

        assert result['status'] == 'success'
        assert 'threshold' in result

    def test_confusion_matrix(self, binary_classification_data):
        """Test confusion matrix in results."""
        result = find_optimal_threshold(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            method='youden'
        )

        assert 'confusion_matrix' in result
        cm = result['confusion_matrix']
        assert 'tp' in cm
        assert 'tn' in cm
        assert 'fp' in cm
        assert 'fn' in cm

    def test_ppv_npv(self, binary_classification_data):
        """Test PPV and NPV in results."""
        result = find_optimal_threshold(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            method='youden'
        )

        assert 'ppv' in result
        assert 'npv' in result
        assert 0 <= result['ppv'] <= 1
        assert 0 <= result['npv'] <= 1


# ==================== Full Evaluation Tests ====================

class TestFullClassifierEvaluation:
    """Tests for full classifier evaluation."""

    def test_full_evaluation(self, binary_classification_data):
        """Test full_classifier_evaluation function."""
        result = full_classifier_evaluation(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert result['status'] == 'success'
        assert 'discrimination' in result
        assert 'calibration' in result
        assert 'optimal_thresholds' in result
        assert 'interpretation' in result

    def test_discrimination_metrics(self, binary_classification_data):
        """Test discrimination metrics in full evaluation."""
        result = full_classifier_evaluation(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        disc = result['discrimination']
        assert 'auc_roc' in disc
        assert 'auc_roc_ci' in disc
        assert 'auc_pr' in disc

    def test_calibration_metrics(self, binary_classification_data):
        """Test calibration metrics in full evaluation."""
        result = full_classifier_evaluation(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        cal = result['calibration']
        assert 'brier_score' in cal

    def test_optimal_thresholds(self, binary_classification_data):
        """Test optimal thresholds in full evaluation."""
        result = full_classifier_evaluation(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        thresholds = result['optimal_thresholds']
        assert 'youden' in thresholds

    def test_interpretation(self, binary_classification_data):
        """Test interpretation in full evaluation."""
        result = full_classifier_evaluation(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        interp = result['interpretation']
        assert 'auc_roc' in interp
        assert 'calibration' in interp


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_small_sample(self):
        """Test with very small sample."""
        y_true = np.array([0, 0, 1, 1, 1])
        y_score = np.array([0.2, 0.3, 0.6, 0.7, 0.9])

        result = compute_roc_curve(y_true, y_score)
        assert 'auc' in result

    def test_extreme_scores(self):
        """Test with extreme prediction scores."""
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.0, 0.0, 1.0, 1.0])

        result = compute_roc_curve(y_true, y_score)
        assert result['auc'] == pytest.approx(1.0, abs=0.01)

    def test_identical_scores(self):
        """Test with identical prediction scores."""
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.5, 0.5, 0.5, 0.5])

        result = compute_roc_curve(y_true, y_score)
        # With identical scores, AUC behavior depends on tie handling
        # Just check it returns a valid AUC
        assert 0 <= result['auc'] <= 1


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow(self, binary_classification_data):
        """Test complete analysis workflow."""
        y_true = binary_classification_data['y_true']
        y_score = binary_classification_data['y_score_good']

        # 1. ROC Analysis
        roc_result = compute_roc_curve(y_true, y_score)
        assert roc_result['auc'] > 0.5

        # 2. Find optimal threshold
        thresh_result = find_optimal_threshold(y_true, y_score, method='youden')
        thresh_result['threshold']

        # 3. Calibration analysis
        cal_result = analyze_calibration(y_true, y_score)
        assert 'brier_score' in cal_result

        # 4. PR analysis
        pr_result = compute_precision_recall(y_true, y_score)
        assert 'auc_pr' in pr_result

        # 5. Full evaluation
        full_result = full_classifier_evaluation(y_true, y_score)

        # Verify consistency
        assert abs(full_result['discrimination']['auc_roc'] - roc_result['auc']) < 0.01

    def test_model_selection_workflow(self, binary_classification_data):
        """Test model selection workflow."""
        y_true = binary_classification_data['y_true']

        # Compare models using DeLong test
        comparison = compare_roc_curves(
            y_true,
            binary_classification_data['y_score_good'],
            binary_classification_data['y_score_poor'],
            'Model A',
            'Model B',
        )

        # Model A (good) should have higher AUC
        assert comparison['model1']['auc'] > comparison['model2']['auc']

        # Get full evaluation for best model
        evaluation = full_classifier_evaluation(
            y_true,
            binary_classification_data['y_score_good']
        )

        # Should show good discrimination
        assert evaluation['discrimination']['auc_roc'] > 0.6


# ==================== Phase 5A: Enhanced Interactive Functions Tests ====================

class TestMultiModelComparison:
    """Tests for compare_multiple_models function."""

    def test_three_model_comparison(self, binary_classification_data):
        """Test comparing three models."""
        y_true = binary_classification_data['y_true']

        models = {
            'Good Model': binary_classification_data['y_score_good'],
            'Poor Model': binary_classification_data['y_score_poor'],
            'Random Model': binary_classification_data['y_score_random'],
        }

        result = compare_multiple_models(y_true, models)

        assert result['status'] == 'success'
        assert result['n_models'] == 3
        assert result['n_comparisons'] == 3  # C(3,2) = 3

        # Check rankings
        assert len(result['model_rankings']) == 3
        assert result['model_rankings'][0]['rank'] == 1

        # Good model should be ranked first
        assert result['model_rankings'][0]['model'] == 'Good Model'

        # Check pairwise comparisons
        assert len(result['pairwise_comparisons']) == 3

    def test_multiple_comparison_correction(self, binary_classification_data):
        """Test different correction methods."""
        y_true = binary_classification_data['y_true']

        models = {
            'Model A': binary_classification_data['y_score_good'],
            'Model B': binary_classification_data['y_score_poor'],
            'Model C': binary_classification_data['y_score_random'],
        }

        # Test Bonferroni
        result_bonf = compare_multiple_models(y_true, models, correction='bonferroni')
        assert 'p_value_adjusted' in result_bonf['pairwise_comparisons'][0]

        # Test Holm
        result_holm = compare_multiple_models(y_true, models, correction='holm')
        assert 'p_value_adjusted' in result_holm['pairwise_comparisons'][0]

        # Test BH
        result_bh = compare_multiple_models(y_true, models, correction='bh')
        assert 'p_value_adjusted' in result_bh['pairwise_comparisons'][0]

        # Test no correction
        result_none = compare_multiple_models(y_true, models, correction='none')
        for comp in result_none['pairwise_comparisons']:
            assert comp['p_value'] == comp['p_value_adjusted']

    def test_best_model_identification(self, binary_classification_data):
        """Test best model is correctly identified."""
        y_true = binary_classification_data['y_true']

        models = {
            'Excellent': binary_classification_data['y_score_good'],
            'Medium': binary_classification_data['y_score_poor'],
        }

        result = compare_multiple_models(y_true, models)

        assert result['best_model']['name'] == 'Excellent'
        assert result['best_model']['auc'] > 0.5

    def test_interpretation_generated(self, binary_classification_data):
        """Test interpretation text is generated."""
        y_true = binary_classification_data['y_true']

        models = {
            'Model 1': binary_classification_data['y_score_good'],
            'Model 2': binary_classification_data['y_score_poor'],
        }

        result = compare_multiple_models(y_true, models)

        assert 'interpretation' in result
        assert 'Multi-Model Comparison' in result['interpretation']
        assert 'Rankings' in result['interpretation']

    def test_two_models(self, binary_classification_data):
        """Test with just two models (minimum)."""
        y_true = binary_classification_data['y_true']

        models = {
            'A': binary_classification_data['y_score_good'],
            'B': binary_classification_data['y_score_poor'],
        }

        result = compare_multiple_models(y_true, models)

        assert result['n_models'] == 2
        assert result['n_comparisons'] == 1

    def test_error_on_single_model(self, binary_classification_data):
        """Test error with only one model."""
        y_true = binary_classification_data['y_true']

        models = {
            'Single': binary_classification_data['y_score_good'],
        }

        with pytest.raises(ValueError, match="Need at least 2 models"):
            compare_multiple_models(y_true, models)


class TestThresholdAnalysis:
    """Tests for threshold_analysis function."""

    def test_basic_threshold_analysis(self, binary_classification_data):
        """Test basic threshold analysis."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert result['status'] == 'success'
        assert 'threshold_table' in result
        assert len(result['threshold_table']) > 0

    def test_threshold_table_metrics(self, binary_classification_data):
        """Test all metrics are included in threshold table."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        row = result['threshold_table'][10]  # Middle threshold

        # Check all required metrics
        assert 'threshold' in row
        assert 'sensitivity' in row
        assert 'specificity' in row
        assert 'ppv' in row
        assert 'npv' in row
        assert 'f1' in row
        assert 'accuracy' in row
        assert 'youden_j' in row
        assert 'confusion_matrix' in row

    def test_target_sensitivity(self, binary_classification_data):
        """Test finding threshold for target sensitivity."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            target_metric='sensitivity',
            target_value=0.90
        )

        assert 'target_threshold' in result
        assert result['target_threshold'] is not None
        assert result['target_threshold']['achieved_value'] >= 0.90

    def test_target_specificity(self, binary_classification_data):
        """Test finding threshold for target specificity."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            target_metric='specificity',
            target_value=0.90
        )

        assert 'target_threshold' in result
        assert result['target_threshold'] is not None

    def test_recommended_thresholds(self, binary_classification_data):
        """Test recommended thresholds are provided."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert 'recommended_thresholds' in result
        assert 'youden_optimal' in result['recommended_thresholds']
        assert 'f1_optimal' in result['recommended_thresholds']

    def test_custom_thresholds(self, binary_classification_data):
        """Test with custom threshold list."""
        custom_thresholds = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]

        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            thresholds=custom_thresholds
        )

        assert len(result['threshold_table']) == len(custom_thresholds)

    def test_clinical_interpretation(self, binary_classification_data):
        """Test clinical interpretation text."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        assert 'clinical_interpretation' in result
        assert 'Clinical Decision Support' in result['clinical_interpretation']

    def test_unachievable_target(self, binary_classification_data):
        """Test behavior when target is unachievable."""
        result = threshold_analysis(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_poor'],
            target_metric='sensitivity',
            target_value=0.99  # Very high target
        )

        # Should still return a result, but may not achieve target
        assert 'target_threshold' in result


class TestPublicationReport:
    """Tests for generate_publication_report function."""

    def test_basic_report_generation(self, binary_classification_data):
        """Test basic report generation."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            model_name="The test model",
            outcome_name="test outcome"
        )

        assert result['status'] == 'success'
        assert 'results_text' in result
        assert 'methods_text' in result
        assert 'table_data' in result
        assert 'figure_data' in result

    def test_results_text_format(self, binary_classification_data):
        """Test results text contains key information."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            model_name="The gradient boosting model",
            outcome_name="30-day mortality"
        )

        results_text = result['results_text']

        # Should contain model name and outcome
        assert 'gradient boosting model' in results_text
        assert '30-day mortality' in results_text

        # Should contain AUC
        assert 'AUC' in results_text or 'area under' in results_text.lower()

        # Should contain CI
        assert '95% CI' in results_text

        # Should contain sensitivity/specificity
        assert 'sensitivity' in results_text
        assert 'specificity' in results_text

    def test_methods_text(self, binary_classification_data):
        """Test methods text is appropriate."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        methods_text = result['methods_text']

        # Should mention DeLong
        assert 'DeLong' in methods_text

        # Should mention bootstrap
        assert 'bootstrap' in methods_text

    def test_table_data_structure(self, binary_classification_data):
        """Test table data has proper structure."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        table_data = result['table_data']

        assert 'title' in table_data
        assert 'metrics' in table_data
        assert len(table_data['metrics']) > 5

        # Check metric structure
        for metric in table_data['metrics']:
            assert 'metric' in metric
            assert 'value' in metric

    def test_figure_data_structure(self, binary_classification_data):
        """Test figure data has ROC curve coordinates."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        figure_data = result['figure_data']

        assert 'roc_curve' in figure_data
        assert 'auc' in figure_data
        assert 'optimal_point' in figure_data

        # Check curve data
        assert len(figure_data['roc_curve']) > 0
        for point in figure_data['roc_curve']:
            assert 'fpr' in point
            assert 'tpr' in point

    def test_all_metrics_included(self, binary_classification_data):
        """Test all metrics are included in all_metrics."""
        result = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good']
        )

        metrics = result['all_metrics']

        # Check essential metrics
        assert 'auc' in metrics
        assert 'auc_ci_lower' in metrics
        assert 'auc_ci_upper' in metrics
        assert 'sensitivity' in metrics
        assert 'specificity' in metrics
        assert 'ppv' in metrics
        assert 'npv' in metrics
        assert 'brier_score' in metrics

    def test_decimal_places(self, binary_classification_data):
        """Test decimal places parameter."""
        result_2 = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            decimal_places=2
        )

        result_3 = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            decimal_places=3
        )

        # Different decimal places should produce different text
        assert result_2['results_text'] != result_3['results_text']

    def test_threshold_method(self, binary_classification_data):
        """Test different threshold methods."""
        result_youden = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            threshold_method='youden'
        )

        assert "Youden" in result_youden['results_text']

        result_f1 = generate_publication_report(
            binary_classification_data['y_true'],
            binary_classification_data['y_score_good'],
            threshold_method='f1'
        )

        assert "F1" in result_f1['results_text']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

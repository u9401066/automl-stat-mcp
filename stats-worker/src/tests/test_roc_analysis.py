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

import pytest
import numpy as np
import pandas as pd
from scipy.special import expit  # logistic function

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tasks.roc_analysis import (
    compute_roc_curve,
    compare_roc_curves,
    analyze_calibration,
    compute_precision_recall,
    find_optimal_threshold,
    full_classifier_evaluation,
    DeLongTest,
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
    n = 200
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
        threshold = thresh_result['threshold']
        
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

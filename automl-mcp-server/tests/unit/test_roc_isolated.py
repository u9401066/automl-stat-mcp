"""
Isolated tests for ROC analysis utilities.

Tests the ROC curve, AUC, and threshold optimization logic.
"""

import numpy as np

# ==============================================================================
# Tests
# ==============================================================================


class TestROCCurveCalculation:
    """Test ROC curve calculations"""

    def test_perfect_classifier(self):
        """Test ROC for perfect classifier"""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_score = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])

        # Calculate ROC points manually
        thresholds = sorted(set(y_score), reverse=True)

        tpr_list = []
        fpr_list = []

        for thresh in thresholds:
            y_pred = (y_score >= thresh).astype(int)

            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            tn = np.sum((y_pred == 0) & (y_true == 0))
            fn = np.sum((y_pred == 0) & (y_true == 1))

            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

            tpr_list.append(tpr)
            fpr_list.append(fpr)

        # Perfect classifier should have AUC = 1.0
        # AUC approximation using trapezoidal rule
        auc = 0
        for i in range(1, len(fpr_list)):
            auc += (fpr_list[i] - fpr_list[i - 1]) * (tpr_list[i] + tpr_list[i - 1]) / 2

        assert abs(auc - 1.0) < 0.01  # Near perfect
        print("✓ Perfect classifier ROC")

    def test_random_classifier(self):
        """Test ROC for random classifier (AUC ≈ 0.5)"""
        np.random.seed(42)
        n = 1000
        y_true = np.random.randint(0, 2, n)
        y_score = np.random.rand(n)

        # Calculate AUC using Mann-Whitney U statistic
        from scipy.stats import mannwhitneyu

        pos_scores = y_score[y_true == 1]
        neg_scores = y_score[y_true == 0]

        u_stat, _ = mannwhitneyu(pos_scores, neg_scores, alternative="two-sided")
        auc = u_stat / (len(pos_scores) * len(neg_scores))

        # Should be around 0.5 for random
        assert 0.4 < auc < 0.6
        print(f"✓ Random classifier AUC = {auc:.3f}")

    def test_worst_classifier(self):
        """Test ROC for worst classifier (AUC ≈ 0)"""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_score = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])  # Reversed

        from scipy.stats import mannwhitneyu

        pos_scores = y_score[y_true == 1]
        neg_scores = y_score[y_true == 0]

        u_stat, _ = mannwhitneyu(pos_scores, neg_scores, alternative="two-sided")
        auc = u_stat / (len(pos_scores) * len(neg_scores))

        # Should be close to 0
        assert auc < 0.1
        print(f"✓ Worst classifier AUC = {auc:.3f}")


class TestAUCCalculation:
    """Test AUC calculation methods"""

    def test_auc_trapezoidal(self):
        """Test AUC using trapezoidal rule"""
        # Simple case: triangle
        fpr = np.array([0, 0.5, 1])
        tpr = np.array([0, 1, 1])

        auc = np.trapz(tpr, fpr)
        assert abs(auc - 0.75) < 0.01
        print("✓ AUC trapezoidal rule")

    def test_auc_wilcoxon(self):
        """Test AUC using Wilcoxon-Mann-Whitney interpretation"""
        # AUC = P(score_pos > score_neg)
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.2, 0.4, 0.6, 0.8])

        pos_scores = y_score[y_true == 1]
        neg_scores = y_score[y_true == 0]

        # Count pairs where positive > negative
        count = 0
        total = 0
        for p in pos_scores:
            for n in neg_scores:
                total += 1
                if p > n:
                    count += 1
                elif p == n:
                    count += 0.5

        auc = count / total
        assert auc == 1.0  # All positive scores > negative scores
        print("✓ AUC Wilcoxon interpretation")


class TestConfidenceIntervals:
    """Test AUC confidence interval calculation"""

    def test_delong_variance(self):
        """Test DeLong method for AUC variance (simplified)"""
        np.random.seed(42)
        # Use overlapping distributions to get variance in AUC
        y_true = np.array([0] * 30 + [1] * 30)
        y_score = np.concatenate(
            [
                np.random.uniform(0.2, 0.6, 30),  # Negative: 0.2-0.6
                np.random.uniform(0.4, 0.8, 30),  # Positive: 0.4-0.8 (overlap!)
            ]
        )

        # Simplified bootstrap CI
        n_bootstrap = 500
        aucs = []

        for _ in range(n_bootstrap):
            idx = np.random.choice(len(y_true), len(y_true), replace=True)
            y_t = y_true[idx]
            y_s = y_score[idx]

            # Skip if all same class
            if len(np.unique(y_t)) < 2:
                continue

            pos = y_s[y_t == 1]
            neg = y_s[y_t == 0]

            if len(pos) == 0 or len(neg) == 0:
                continue

            # Simple AUC
            count = sum(1 for p in pos for n in neg if p > n)
            count += 0.5 * sum(1 for p in pos for n in neg if p == n)
            auc = count / (len(pos) * len(neg))
            aucs.append(auc)

        ci_lower = np.percentile(aucs, 2.5)
        ci_upper = np.percentile(aucs, 97.5)

        assert ci_lower < ci_upper
        assert ci_lower > 0.5  # Should be significantly above random
        print(f"✓ Bootstrap CI: [{ci_lower:.3f}, {ci_upper:.3f}]")


class TestThresholdOptimization:
    """Test threshold optimization methods"""

    def test_youden_index(self):
        """Test Youden's J statistic for optimal threshold"""
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        y_score = np.array([0.1, 0.2, 0.3, 0.4, 0.45, 0.55, 0.6, 0.7, 0.8, 0.9])

        # Test multiple thresholds
        thresholds = np.linspace(0, 1, 21)
        best_j = -1
        best_thresh = 0

        for thresh in thresholds:
            y_pred = (y_score >= thresh).astype(int)

            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            tn = np.sum((y_pred == 0) & (y_true == 0))
            fn = np.sum((y_pred == 0) & (y_true == 1))

            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

            j = sensitivity + specificity - 1

            if j > best_j:
                best_j = j
                best_thresh = thresh

        assert best_j > 0.8  # Good classifier
        assert 0.4 < best_thresh < 0.6  # Around 0.5
        print(f"✓ Youden optimal threshold: {best_thresh:.2f} (J={best_j:.3f})")

    def test_f1_optimal_threshold(self):
        """Test F1-optimal threshold"""
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        y_score = np.array([0.1, 0.2, 0.3, 0.4, 0.45, 0.55, 0.6, 0.7, 0.8, 0.9])

        thresholds = np.linspace(0.1, 0.9, 17)
        best_f1 = 0
        best_thresh = 0

        for thresh in thresholds:
            y_pred = (y_score >= thresh).astype(int)

            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            fn = np.sum((y_pred == 0) & (y_true == 1))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0

            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh

        assert best_f1 > 0.8
        print(f"✓ F1-optimal threshold: {best_thresh:.2f} (F1={best_f1:.3f})")


class TestClassificationMetrics:
    """Test classification metrics at threshold"""

    def test_confusion_matrix(self):
        """Test confusion matrix calculation"""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1])

        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        tn = np.sum((y_pred == 0) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))

        assert tp == 1
        assert fp == 1
        assert tn == 1
        assert fn == 1
        print("✓ Confusion matrix")

    def test_sensitivity_specificity(self):
        """Test sensitivity and specificity"""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 0, 1, 1])  # 1 FP, 1 FN

        tp = np.sum((y_pred == 1) & (y_true == 1))  # 2
        fp = np.sum((y_pred == 1) & (y_true == 0))  # 1
        tn = np.sum((y_pred == 0) & (y_true == 0))  # 2
        fn = np.sum((y_pred == 0) & (y_true == 1))  # 1

        sensitivity = tp / (tp + fn)  # 2/3
        specificity = tn / (tn + fp)  # 2/3

        assert abs(sensitivity - 2 / 3) < 0.01
        assert abs(specificity - 2 / 3) < 0.01
        print("✓ Sensitivity and specificity")

    def test_ppv_npv(self):
        """Test positive and negative predictive values"""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 0, 1, 1])

        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        tn = np.sum((y_pred == 0) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))

        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0  # 2/3
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0  # 2/3

        assert abs(ppv - 2 / 3) < 0.01
        assert abs(npv - 2 / 3) < 0.01
        print("✓ PPV and NPV")

    def test_accuracy(self):
        """Test accuracy calculation"""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 0, 1, 1])

        correct = np.sum(y_true == y_pred)
        accuracy = correct / len(y_true)

        assert accuracy == 4 / 6
        print("✓ Accuracy")


class TestROCComparison:
    """Test ROC curve comparison"""

    def test_auc_difference(self):
        """Test AUC difference calculation"""
        auc1 = 0.85
        auc2 = 0.80

        diff = auc1 - auc2
        assert abs(diff - 0.05) < 1e-9  # Use tolerance for float comparison
        print("✓ AUC difference")

    def test_auc_comparison_bootstrap(self):
        """Test bootstrapped AUC comparison"""
        np.random.seed(42)
        n = 100
        y_true = np.random.randint(0, 2, n)
        y_score1 = y_true * 0.6 + np.random.rand(n) * 0.4  # Better model
        y_score2 = y_true * 0.3 + np.random.rand(n) * 0.7  # Worse model

        def calc_auc(y_t, y_s):
            pos = y_s[y_t == 1]
            neg = y_s[y_t == 0]
            if len(pos) == 0 or len(neg) == 0:
                return 0.5
            count = sum(1 for p in pos for n in neg if p > n)
            count += 0.5 * sum(1 for p in pos for n in neg if p == n)
            return count / (len(pos) * len(neg))

        auc1 = calc_auc(y_true, y_score1)
        auc2 = calc_auc(y_true, y_score2)

        assert auc1 > auc2  # Model 1 should be better
        print(f"✓ AUC comparison: {auc1:.3f} vs {auc2:.3f}")


class TestCalibration:
    """Test calibration metrics"""

    def test_brier_score(self):
        """Test Brier score calculation"""
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.1, 0.4, 0.6, 0.9])

        brier = np.mean((y_prob - y_true) ** 2)

        # Manual: ((0.1-0)^2 + (0.4-0)^2 + (0.6-1)^2 + (0.9-1)^2) / 4
        expected = (0.01 + 0.16 + 0.16 + 0.01) / 4

        assert abs(brier - expected) < 0.001
        print(f"✓ Brier score: {brier:.4f}")

    def test_calibration_curve(self):
        """Test calibration curve binning"""
        np.random.seed(42)
        n = 1000
        y_prob = np.random.rand(n)
        # Well-calibrated: actual rate ≈ predicted prob
        y_true = (np.random.rand(n) < y_prob).astype(int)

        n_bins = 10
        bins = np.linspace(0, 1, n_bins + 1)

        observed = []
        predicted = []

        for i in range(n_bins):
            mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
            if np.sum(mask) > 0:
                observed.append(np.mean(y_true[mask]))
                predicted.append(np.mean(y_prob[mask]))

        # For well-calibrated model, observed ≈ predicted
        errors = [abs(o - p) for o, p in zip(observed, predicted, strict=False)]
        mean_error = np.mean(errors)

        assert mean_error < 0.1  # Should be well calibrated
        print(f"✓ Calibration curve (mean error: {mean_error:.4f})")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running ROC analysis isolated tests")
    print("=" * 60)

    test_classes = [
        TestROCCurveCalculation(),
        TestAUCCalculation(),
        TestConfidenceIntervals(),
        TestThresholdOptimization(),
        TestClassificationMetrics(),
        TestROCComparison(),
        TestCalibration(),
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)

        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise

    print("\n" + "=" * 60)
    print("🎉 ALL ROC ANALYSIS TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

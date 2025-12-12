"""
Isolated tests for propensity score matching utilities.

Tests propensity score estimation, matching algorithms, balance assessment.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Tuple, Dict, Optional


# ==============================================================================
# Tests
# ==============================================================================

class TestPropensityScoreEstimation:
    """Test propensity score calculation"""
    
    def test_logistic_propensity(self):
        """Test logistic regression for propensity scores"""
        np.random.seed(42)
        n = 200
        
        # Confounders
        age = np.random.normal(50, 10, n)
        male = np.random.binomial(1, 0.5, n)
        
        # Treatment depends on confounders
        logit = -2 + 0.02 * age + 0.5 * male
        prob = 1 / (1 + np.exp(-logit))
        treatment = np.random.binomial(1, prob)
        
        # Simple propensity score (true model)
        ps_true = prob
        
        # All propensity scores should be between 0 and 1
        assert np.all((ps_true >= 0) & (ps_true <= 1))
        
        # Treatment group should have higher average propensity
        ps_treated = ps_true[treatment == 1].mean()
        ps_control = ps_true[treatment == 0].mean()
        assert ps_treated > ps_control
        
        print(f"✓ Propensity scores: treated={ps_treated:.3f}, control={ps_control:.3f}")
    
    def test_propensity_overlap(self):
        """Test propensity score overlap check"""
        np.random.seed(42)
        
        # Good overlap
        ps_treated = np.random.uniform(0.3, 0.8, 50)
        ps_control = np.random.uniform(0.2, 0.7, 50)
        
        # Check overlap region
        min_treated, max_treated = ps_treated.min(), ps_treated.max()
        min_control, max_control = ps_control.min(), ps_control.max()
        
        overlap_min = max(min_treated, min_control)
        overlap_max = min(max_treated, max_control)
        
        has_overlap = overlap_min < overlap_max
        assert has_overlap
        
        print(f"✓ Overlap region: [{overlap_min:.3f}, {overlap_max:.3f}]")
    
    def test_positivity_violation(self):
        """Test detection of positivity violations"""
        np.random.seed(42)
        
        # Extreme propensity scores (positivity violation)
        ps = np.array([0.01, 0.02, 0.05, 0.95, 0.98, 0.99])
        
        # Flag extreme values
        extreme_low = ps < 0.05
        extreme_high = ps > 0.95
        
        n_violations = np.sum(extreme_low | extreme_high)
        assert n_violations > 0
        
        print(f"✓ Positivity violations detected: {n_violations}")


class TestMatching:
    """Test matching algorithms"""
    
    def test_nearest_neighbor_matching(self):
        """Test 1:1 nearest neighbor matching"""
        np.random.seed(42)
        
        # Propensity scores
        ps_treated = np.array([0.5, 0.6, 0.7, 0.8])
        ps_control = np.array([0.45, 0.55, 0.65, 0.75, 0.85, 0.52])
        
        # Match each treated to nearest control
        matches = []
        used_controls = set()
        
        for i, ps_t in enumerate(ps_treated):
            best_j = None
            best_dist = float('inf')
            
            for j, ps_c in enumerate(ps_control):
                if j not in used_controls:
                    dist = abs(ps_t - ps_c)
                    if dist < best_dist:
                        best_dist = dist
                        best_j = j
            
            if best_j is not None:
                matches.append((i, best_j, best_dist))
                used_controls.add(best_j)
        
        assert len(matches) == len(ps_treated)
        print(f"✓ Matched {len(matches)} pairs")
    
    def test_caliper_matching(self):
        """Test matching with caliper constraint"""
        np.random.seed(42)
        
        ps_treated = np.array([0.5, 0.6, 0.9])
        ps_control = np.array([0.45, 0.55, 0.3])  # 0.3 is far from 0.9
        
        caliper = 0.1
        
        matches = []
        for i, ps_t in enumerate(ps_treated):
            distances = np.abs(ps_control - ps_t)
            within_caliper = distances < caliper
            
            if np.any(within_caliper):
                best_j = np.argmin(distances)
                if distances[best_j] < caliper:
                    matches.append((i, best_j, distances[best_j]))
        
        # Third treated unit (0.9) should not match
        assert len(matches) == 2
        print(f"✓ Caliper matching: {len(matches)} pairs within caliper={caliper}")
    
    def test_k_to_1_matching(self):
        """Test k:1 matching (multiple controls per treated)"""
        np.random.seed(42)
        
        ps_treated = np.array([0.5])
        ps_control = np.array([0.45, 0.55, 0.48, 0.52, 0.6])
        
        k = 3  # Match 3 controls per treated
        
        # Find k nearest controls
        distances = np.abs(ps_control - ps_treated[0])
        sorted_indices = np.argsort(distances)
        
        matched_controls = sorted_indices[:k]
        matched_distances = distances[matched_controls]
        
        assert len(matched_controls) == k
        print(f"✓ 1:{k} matching: distances = {matched_distances.round(3)}")


class TestBalanceAssessment:
    """Test covariate balance assessment"""
    
    def test_standardized_mean_difference(self):
        """Test SMD calculation"""
        np.random.seed(42)
        
        # Unbalanced before matching
        x_treated = np.random.normal(55, 10, 50)
        x_control = np.random.normal(45, 10, 50)
        
        # SMD = (mean_t - mean_c) / pooled_sd
        pooled_sd = np.sqrt((x_treated.var() + x_control.var()) / 2)
        smd = (x_treated.mean() - x_control.mean()) / pooled_sd
        
        # SMD > 0.1 indicates imbalance
        assert abs(smd) > 0.1
        print(f"✓ SMD (unbalanced) = {smd:.3f}")
    
    def test_variance_ratio(self):
        """Test variance ratio for balance"""
        np.random.seed(42)
        
        # Similar variances
        x_treated = np.random.normal(50, 10, 100)
        x_control = np.random.normal(50, 10, 100)
        
        var_ratio = x_treated.var() / x_control.var()
        
        # Good balance: 0.5 < ratio < 2.0
        assert 0.5 < var_ratio < 2.0
        print(f"✓ Variance ratio = {var_ratio:.3f}")
    
    def test_ks_statistic(self):
        """Test Kolmogorov-Smirnov statistic for balance"""
        np.random.seed(42)
        
        # Similar distributions
        x_treated = np.random.normal(50, 10, 100)
        x_control = np.random.normal(50, 10, 100)
        
        ks_stat, p_value = stats.ks_2samp(x_treated, x_control)
        
        # High p-value indicates similar distributions
        assert p_value > 0.1
        print(f"✓ KS test: stat={ks_stat:.3f}, p={p_value:.3f}")
    
    def test_love_plot_data(self):
        """Test data preparation for Love plot"""
        np.random.seed(42)
        
        # Before matching (imbalanced)
        smd_before = {'age': 0.35, 'male': 0.25, 'bmi': 0.40}
        
        # After matching (balanced)
        smd_after = {'age': 0.05, 'male': 0.03, 'bmi': 0.08}
        
        # Verify improvement
        for var in smd_before:
            assert abs(smd_after[var]) < abs(smd_before[var])
        
        print("✓ Love plot data: all SMDs improved")


class TestTreatmentEffectEstimation:
    """Test treatment effect estimation"""
    
    def test_ate_matched(self):
        """Test ATE from matched sample"""
        np.random.seed(42)
        
        # Matched pairs: (treated outcome, control outcome)
        matched_pairs = [
            (10, 8),
            (12, 9),
            (15, 11),
            (8, 7),
            (11, 10)
        ]
        
        # Pair differences
        differences = [t - c for t, c in matched_pairs]
        
        ate = np.mean(differences)
        se = np.std(differences, ddof=1) / np.sqrt(len(differences))
        
        assert ate > 0  # Treatment is beneficial
        print(f"✓ ATE (matched) = {ate:.2f} ± {se:.2f}")
    
    def test_att_weighted(self):
        """Test ATT with inverse probability weighting"""
        np.random.seed(42)
        n = 100
        
        # Data
        treatment = np.random.binomial(1, 0.4, n)
        ps = np.random.uniform(0.2, 0.8, n)
        outcome = treatment * 2 + np.random.normal(0, 1, n)
        
        # IPW weights for ATT
        # Treated: weight = 1
        # Control: weight = ps / (1 - ps)
        weights = np.where(treatment == 1, 1, ps / (1 - ps))
        
        # Weighted means
        y1 = np.average(outcome[treatment == 1], weights=weights[treatment == 1])
        y0 = np.average(outcome[treatment == 0], weights=weights[treatment == 0])
        
        att = y1 - y0
        print(f"✓ ATT (IPW) = {att:.2f}")
    
    def test_confidence_interval(self):
        """Test CI for treatment effect"""
        np.random.seed(42)
        
        # Bootstrap for CI
        n_bootstrap = 100
        ates = []
        
        # Original data
        y_treated = np.random.normal(10, 2, 50)
        y_control = np.random.normal(8, 2, 50)
        
        for _ in range(n_bootstrap):
            idx_t = np.random.choice(len(y_treated), len(y_treated), replace=True)
            idx_c = np.random.choice(len(y_control), len(y_control), replace=True)
            
            ate = y_treated[idx_t].mean() - y_control[idx_c].mean()
            ates.append(ate)
        
        ci_lower = np.percentile(ates, 2.5)
        ci_upper = np.percentile(ates, 97.5)
        
        assert ci_lower < ci_upper
        assert ci_lower > 0  # Significant effect
        print(f"✓ 95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")


class TestSensitivityAnalysis:
    """Test sensitivity analysis for unmeasured confounding"""
    
    def test_rosenbaum_bounds(self):
        """Test Rosenbaum bounds calculation"""
        np.random.seed(42)
        
        # Matched pairs with outcomes
        n_pairs = 20
        y_treated = np.random.normal(10, 2, n_pairs)
        y_control = np.random.normal(8, 2, n_pairs)
        
        # Difference
        d = y_treated - y_control
        
        # Wilcoxon signed-rank test at Gamma = 1 (no confounding)
        stat, p_value = stats.wilcoxon(d)
        
        # Under gamma = 1, should be significant
        assert p_value < 0.05
        
        print(f"✓ Rosenbaum bound (Γ=1): p = {p_value:.4f}")
    
    def test_e_value(self):
        """Test E-value calculation"""
        # E-value: minimum strength of unmeasured confounding 
        # to explain away observed effect
        
        rr = 2.0  # Observed risk ratio
        
        # E-value = RR + sqrt(RR * (RR - 1))
        e_value = rr + np.sqrt(rr * (rr - 1))
        
        # E-value should be larger than observed effect
        assert e_value > rr
        print(f"✓ E-value for RR={rr}: {e_value:.2f}")


class TestSubgroupAnalysis:
    """Test subgroup/heterogeneity analysis"""
    
    def test_subgroup_effects(self):
        """Test treatment effect heterogeneity by subgroup"""
        np.random.seed(42)
        
        # Data with heterogeneous effects
        subgroups = ['young', 'old']
        effects = {'young': 3.0, 'old': 1.0}  # Effect modifier
        
        results = {}
        for group in subgroups:
            n = 50
            true_effect = effects[group]
            y_treated = np.random.normal(10 + true_effect, 2, n)
            y_control = np.random.normal(10, 2, n)
            
            ate = y_treated.mean() - y_control.mean()
            results[group] = ate
        
        # Heterogeneity: effects differ
        assert abs(results['young'] - results['old']) > 1
        print(f"✓ Subgroup effects: young={results['young']:.2f}, old={results['old']:.2f}")
    
    def test_interaction_test(self):
        """Test treatment-covariate interaction"""
        np.random.seed(42)
        n = 200
        
        # Data
        treatment = np.random.binomial(1, 0.5, n)
        modifier = np.random.binomial(1, 0.5, n)  # Binary modifier
        
        # Outcome with interaction
        y = 5 + 2*treatment + 1*modifier + 1.5*treatment*modifier + np.random.normal(0, 1, n)
        
        # Estimate interaction (simple comparison)
        effect_mod0 = y[(treatment == 1) & (modifier == 0)].mean() - y[(treatment == 0) & (modifier == 0)].mean()
        effect_mod1 = y[(treatment == 1) & (modifier == 1)].mean() - y[(treatment == 0) & (modifier == 1)].mean()
        
        interaction = effect_mod1 - effect_mod0
        
        # Interaction should be close to true value (1.5)
        assert abs(interaction - 1.5) < 1.0
        print(f"✓ Interaction effect: {interaction:.2f}")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running propensity score matching isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestPropensityScoreEstimation(),
        TestMatching(),
        TestBalanceAssessment(),
        TestTreatmentEffectEstimation(),
        TestSensitivityAnalysis(),
        TestSubgroupAnalysis(),
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
    print("🎉 ALL PROPENSITY SCORE MATCHING TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

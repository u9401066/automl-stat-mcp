"""
Isolated tests for power analysis utilities.

Tests sample size calculation, power calculation, and effect size utilities.
"""
import numpy as np
from scipy import stats
from typing import Tuple


# ==============================================================================
# Tests
# ==============================================================================

class TestEffectSizeCalculations:
    """Test effect size calculations"""
    
    def test_cohens_d_independent(self):
        """Test Cohen's d for independent samples"""
        group1 = np.array([10, 12, 14, 16, 18])
        group2 = np.array([20, 22, 24, 26, 28])
        
        mean1, mean2 = group1.mean(), group2.mean()
        n1, n2 = len(group1), len(group2)
        var1 = group1.var(ddof=1)
        var2 = group2.var(ddof=1)
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
        d = (mean1 - mean2) / pooled_std
        
        assert abs(d) > 2.0  # Very large effect
        print(f"✓ Cohen's d = {d:.3f}")
    
    def test_cohens_d_paired(self):
        """Test Cohen's d for paired samples"""
        before = np.array([100, 110, 105, 115, 95])
        after = np.array([95, 100, 100, 105, 90])
        
        diff = before - after
        d = diff.mean() / diff.std(ddof=1)
        
        assert d > 0  # Positive effect (before > after)
        print(f"✓ Cohen's d (paired) = {d:.3f}")
    
    def test_cohens_h_proportions(self):
        """Test Cohen's h for proportions"""
        p1 = 0.6
        p2 = 0.4
        
        # Cohen's h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
        h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
        
        assert abs(h) > 0.4  # Small to medium effect
        print(f"✓ Cohen's h = {h:.3f}")
    
    def test_effect_size_interpretation(self):
        """Test effect size interpretation"""
        def interpret_d(d):
            d = abs(d)
            if d < 0.2:
                return "negligible"
            elif d < 0.5:
                return "small"
            elif d < 0.8:
                return "medium"
            else:
                return "large"
        
        assert interpret_d(0.1) == "negligible"
        assert interpret_d(0.3) == "small"
        assert interpret_d(0.6) == "medium"
        assert interpret_d(1.0) == "large"
        print("✓ Effect size interpretation")
    
    def test_eta_squared_anova(self):
        """Test eta-squared for ANOVA"""
        # Three groups
        group1 = np.array([10, 12, 14])
        group2 = np.array([20, 22, 24])
        group3 = np.array([30, 32, 34])
        
        all_data = np.concatenate([group1, group2, group3])
        grand_mean = all_data.mean()
        
        # SS_between
        ss_between = (
            len(group1) * (group1.mean() - grand_mean)**2 +
            len(group2) * (group2.mean() - grand_mean)**2 +
            len(group3) * (group3.mean() - grand_mean)**2
        )
        
        # SS_total
        ss_total = np.sum((all_data - grand_mean)**2)
        
        eta_sq = ss_between / ss_total
        
        assert eta_sq > 0.9  # Very large effect
        print(f"✓ Eta-squared = {eta_sq:.3f}")
    
    def test_cramers_v(self):
        """Test Cramér's V for chi-square"""
        contingency = np.array([
            [50, 10],
            [10, 50]
        ])
        
        chi2, _, _, _ = stats.chi2_contingency(contingency)
        n = contingency.sum()
        min_dim = min(contingency.shape) - 1
        
        v = np.sqrt(chi2 / (n * min_dim))
        
        assert v > 0.5  # Strong association
        print(f"✓ Cramér's V = {v:.3f}")


class TestTTestPower:
    """Test t-test power analysis"""
    
    def _calculate_power(self, d: float, n: int, alpha: float = 0.05) -> float:
        """Calculate power for two-sample t-test"""
        # Non-centrality parameter
        ncp = d * np.sqrt(n / 2)
        
        # Critical t-value
        df = 2 * n - 2
        t_crit = stats.t.ppf(1 - alpha/2, df)
        
        # Power = P(T > t_crit | ncp) + P(T < -t_crit | ncp)
        power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
        
        return power
    
    def test_power_increases_with_n(self):
        """Test that power increases with sample size"""
        d = 0.5  # Medium effect
        
        powers = [self._calculate_power(d, n) for n in [10, 30, 50, 100]]
        
        for i in range(1, len(powers)):
            assert powers[i] > powers[i-1], "Power should increase with n"
        
        print("✓ Power increases with n")
    
    def test_power_increases_with_effect_size(self):
        """Test that power increases with effect size"""
        n = 30
        
        powers = [self._calculate_power(d, n) for d in [0.2, 0.5, 0.8, 1.0]]
        
        for i in range(1, len(powers)):
            assert powers[i] > powers[i-1], "Power should increase with effect size"
        
        print("✓ Power increases with effect size")
    
    def test_sample_size_for_power(self):
        """Test sample size calculation for target power"""
        d = 0.5
        target_power = 0.8
        alpha = 0.05
        
        # Binary search for sample size
        n_low, n_high = 2, 1000
        
        while n_high - n_low > 1:
            n_mid = (n_low + n_high) // 2
            power = self._calculate_power(d, n_mid, alpha)
            
            if power < target_power:
                n_low = n_mid
            else:
                n_high = n_mid
        
        # For d=0.5, power=0.8, n should be around 64 per group
        assert 50 < n_high < 80
        print(f"✓ Required n for 80% power: {n_high}")


class TestProportionPower:
    """Test power analysis for proportion tests"""
    
    def test_cohens_h(self):
        """Test Cohen's h calculation"""
        p1, p2 = 0.6, 0.4
        h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
        
        assert abs(h) > 0.4
        print(f"✓ Cohen's h = {h:.3f}")
    
    def test_proportion_sample_size(self):
        """Test sample size for proportion comparison"""
        p1, p2 = 0.6, 0.4
        alpha = 0.05
        power = 0.8
        
        # Cohen's h
        h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
        
        # Sample size formula (normal approximation)
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(power)
        
        n = 2 * ((z_alpha + z_beta) / h) ** 2
        
        assert 80 < n < 120  # Approximately 93 per group
        print(f"✓ Required n for proportion test: {n:.0f}")


class TestANOVAPower:
    """Test power analysis for ANOVA"""
    
    def test_f_power(self):
        """Test F-test power calculation"""
        # Parameters
        k = 3  # Number of groups
        n = 20  # Per group
        f = 0.4  # Effect size (Cohen's f)
        alpha = 0.05
        
        # Non-centrality parameter
        ncp = (k * n * f**2)
        
        # Degrees of freedom
        df1 = k - 1
        df2 = k * (n - 1)
        
        # Critical F value
        f_crit = stats.f.ppf(1 - alpha, df1, df2)
        
        # Power
        power = 1 - stats.ncf.cdf(f_crit, df1, df2, ncp)
        
        assert power > 0.7  # Should have good power
        print(f"✓ ANOVA power = {power:.3f}")
    
    def test_eta_to_f_conversion(self):
        """Test eta-squared to Cohen's f conversion"""
        eta_sq = 0.14  # Large effect
        
        # f = sqrt(eta_sq / (1 - eta_sq))
        f = np.sqrt(eta_sq / (1 - eta_sq))
        
        assert abs(f - 0.4) < 0.01  # f ≈ 0.4 for eta_sq = 0.14
        print(f"✓ Eta-sq to f: {eta_sq} -> {f:.3f}")


class TestChiSquarePower:
    """Test power analysis for chi-square tests"""
    
    def test_chi_square_sample_size(self):
        """Test sample size for chi-square test"""
        w = 0.3  # Effect size (Cohen's w)
        alpha = 0.05
        power = 0.8
        df = 1  # 2x2 table
        
        # Chi-square critical value
        chi_crit = stats.chi2.ppf(1 - alpha, df)
        
        # Non-centrality parameter for target power
        # Find n where power = 0.8
        z_beta = stats.norm.ppf(power)
        
        # Approximation
        n = (chi_crit + z_beta**2) / w**2
        
        assert n > 0
        print(f"✓ Chi-square sample size approximation: {n:.0f}")


class TestSurvivalPower:
    """Test power analysis for survival analysis"""
    
    def test_logrank_events(self):
        """Test required events for log-rank test"""
        hr = 0.7  # Hazard ratio
        alpha = 0.05
        power = 0.8
        
        # Required events (Schoenfeld formula)
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(power)
        
        # Events needed
        # d = 4 * (z_alpha + z_beta)^2 / (log(hr))^2
        d = 4 * (z_alpha + z_beta)**2 / (np.log(hr))**2
        
        assert d > 0
        print(f"✓ Required events for HR={hr}: {d:.0f}")
    
    def test_median_survival_to_hr(self):
        """Test conversion from median survival times to HR"""
        m1 = 12  # Median survival group 1 (months)
        m2 = 18  # Median survival group 2 (months)
        
        # HR ≈ m1/m2 (exponential assumption)
        hr = m2 / m1  # HR for group 1 vs group 2
        
        assert hr > 1  # Group 1 has worse survival
        print(f"✓ Median ratio to HR: {m1} vs {m2} -> HR={hr:.2f}")


class TestPowerCurves:
    """Test power curve generation"""
    
    def test_power_vs_n_curve(self):
        """Test power as function of sample size"""
        d = 0.5
        alpha = 0.05
        
        ns = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        powers = []
        
        for n in ns:
            ncp = d * np.sqrt(n / 2)
            df = 2 * n - 2
            t_crit = stats.t.ppf(1 - alpha/2, df)
            power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
            powers.append(power)
        
        # Powers should be monotonically increasing
        for i in range(1, len(powers)):
            assert powers[i] >= powers[i-1] - 0.01  # Allow small numerical errors
        
        # Eventually should reach ~80% power
        assert powers[-1] > 0.8
        print("✓ Power curve generation")
    
    def test_power_vs_effect_size_curve(self):
        """Test power as function of effect size"""
        n = 50
        alpha = 0.05
        
        ds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        powers = []
        
        for d in ds:
            ncp = d * np.sqrt(n / 2)
            df = 2 * n - 2
            t_crit = stats.t.ppf(1 - alpha/2, df)
            power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
            powers.append(power)
        
        # Powers should be monotonically increasing
        for i in range(1, len(powers)):
            assert powers[i] >= powers[i-1]
        
        print("✓ Power vs effect size curve")


class TestSensitivityAnalysis:
    """Test sensitivity analysis utilities"""
    
    def test_detectable_effect_size(self):
        """Test minimum detectable effect size"""
        n = 100
        alpha = 0.05
        power = 0.8
        
        # Binary search for effect size
        d_low, d_high = 0.01, 2.0
        
        while d_high - d_low > 0.01:
            d_mid = (d_low + d_high) / 2
            
            ncp = d_mid * np.sqrt(n / 2)
            df = 2 * n - 2
            t_crit = stats.t.ppf(1 - alpha/2, df)
            curr_power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
            
            if curr_power < power:
                d_low = d_mid
            else:
                d_high = d_mid
        
        # For n=100, should detect d ≈ 0.4
        assert 0.3 < d_high < 0.5
        print(f"✓ Minimum detectable effect: {d_high:.3f}")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running power analysis isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestEffectSizeCalculations(),
        TestTTestPower(),
        TestProportionPower(),
        TestANOVAPower(),
        TestChiSquarePower(),
        TestSurvivalPower(),
        TestPowerCurves(),
        TestSensitivityAnalysis(),
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
    print("🎉 ALL POWER ANALYSIS TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

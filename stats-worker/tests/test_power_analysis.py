"""
Test Suite for Power Analysis Module - Phase 6.1

Tests for:
- T-test power analysis (two-sample, paired, one-sample)
- Proportion test power analysis (two-sample, one-sample)
- Effect size calculations
- Sensitivity analysis
"""
import pytest
import math
from typing import Dict, Any

from src.tasks.power_analysis import (
    # Classes
    TTestPowerAnalysis,
    ProportionPowerAnalysis,
    PowerAnalysisResult,
    # Helper functions
    cohens_d_from_means,
    cohens_h_from_proportions,
    interpret_effect_size,
    safe_round,
    # Convenience functions
    calculate_ttest_sample_size,
    calculate_ttest_power,
    calculate_proportion_sample_size,
    calculate_proportion_power,
)


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions"""
    
    def test_safe_round_normal(self):
        """Test safe_round with normal values"""
        assert safe_round(3.14159, 2) == 3.14
        assert safe_round(3.14159, 4) == 3.1416
        assert safe_round(0.0, 2) == 0.0
    
    def test_safe_round_edge_cases(self):
        """Test safe_round with edge cases"""
        assert safe_round(None) is None
        assert safe_round(float('nan')) is None
        assert safe_round(float('inf')) is None
        assert safe_round(float('-inf')) is None
    
    def test_cohens_d_from_means_basic(self):
        """Test Cohen's d calculation from means"""
        # Effect size of 0.5 (medium)
        d = cohens_d_from_means(mean1=105, mean2=100, sd1=10, sd2=10)
        assert abs(d - 0.5) < 0.01
    
    def test_cohens_d_from_means_large_effect(self):
        """Test Cohen's d with large effect"""
        d = cohens_d_from_means(mean1=110, mean2=100, sd1=10, sd2=10)
        assert abs(d - 1.0) < 0.01
    
    def test_cohens_d_from_means_negative(self):
        """Test Cohen's d with reversed means (negative effect)"""
        d = cohens_d_from_means(mean1=95, mean2=100, sd1=10)
        assert d < 0
        assert abs(d) == pytest.approx(0.5, rel=0.01)
    
    def test_cohens_h_from_proportions(self):
        """Test Cohen's h calculation from proportions"""
        # 30% vs 50% should give medium effect
        h = cohens_h_from_proportions(0.30, 0.50)
        assert abs(h) > 0.3  # Should be substantial effect
    
    def test_cohens_h_equal_proportions(self):
        """Test Cohen's h with equal proportions"""
        h = cohens_h_from_proportions(0.50, 0.50)
        assert h == pytest.approx(0.0, abs=0.001)
    
    def test_interpret_effect_size_cohens_d(self):
        """Test effect size interpretation for Cohen's d"""
        assert interpret_effect_size(0.1, "cohens_d") == "negligible"
        assert interpret_effect_size(0.3, "cohens_d") == "small"
        assert interpret_effect_size(0.5, "cohens_d") == "medium"
        assert interpret_effect_size(0.9, "cohens_d") == "large"
    
    def test_interpret_effect_size_negative(self):
        """Test interpretation with negative effect size"""
        assert interpret_effect_size(-0.8, "cohens_d") == "large"


# =============================================================================
# T-Test Power Analysis Tests
# =============================================================================

class TestTTestSampleSize:
    """Tests for t-test sample size calculation"""
    
    def test_two_sample_medium_effect(self):
        """Test two-sample t-test with medium effect size"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert result.test_type == "two-sample t-test"
        assert result.scenario == "sample_size"
        assert result.sample_size_per_group is not None
        assert result.sample_size_per_group > 50  # Should need ~64 per group
        assert result.sample_size_per_group < 80
        assert result.power == 0.80
        assert result.effect_size == 0.5
    
    def test_two_sample_small_effect(self):
        """Test two-sample t-test with small effect size"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.2,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Small effect requires larger sample
        assert result.sample_size_per_group > 300
        assert result.effect_size_interpretation == "small"
    
    def test_two_sample_large_effect(self):
        """Test two-sample t-test with large effect size"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.8,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Large effect requires smaller sample
        assert result.sample_size_per_group < 30
        assert result.effect_size_interpretation == "large"
    
    def test_two_sample_from_means(self):
        """Test sample size calculation from means and SD"""
        result = TTestPowerAnalysis.calculate_sample_size(
            mean1=105,
            mean2=100,
            sd=10,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Effect size should be calculated as 0.5
        assert result.effect_size == pytest.approx(0.5, rel=0.01)
        assert result.mean1 == 105
        assert result.mean2 == 100
        assert result.sd == 10
    
    def test_two_sample_unequal_groups(self):
        """Test with unequal group size ratio"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            ratio=2.0,  # n2 = 2 * n1
            test_type="two-sample",
        )
        
        assert result.ratio == 2.0
        assert result.total_sample_size > result.sample_size_per_group * 2
    
    def test_two_sample_one_sided(self):
        """Test one-sided t-test"""
        result_two = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            alternative="two-sided",
            test_type="two-sample",
        )
        
        result_one = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            alternative="larger",
            test_type="two-sample",
        )
        
        # One-sided test needs fewer samples
        assert result_one.sample_size_per_group < result_two.sample_size_per_group
    
    def test_paired_ttest(self):
        """Test paired t-test sample size"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="paired",
        )
        
        assert result.test_type == "paired t-test"
        # Paired tests are generally more powerful (need fewer samples)
        assert result.sample_size_per_group < 40
    
    def test_one_sample_ttest(self):
        """Test one-sample t-test sample size"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="one-sample",
        )
        
        assert result.test_type == "one-sample t-test"
        assert result.sample_size_per_group == result.total_sample_size
    
    def test_high_power_requirement(self):
        """Test with 90% power requirement"""
        result_80 = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        result_90 = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.90,
            test_type="two-sample",
        )
        
        # Higher power needs more samples
        assert result_90.sample_size_per_group > result_80.sample_size_per_group
    
    def test_stricter_alpha(self):
        """Test with stricter alpha (0.01)"""
        result_05 = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        result_01 = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.01,
            power=0.80,
            test_type="two-sample",
        )
        
        # Stricter alpha needs more samples
        assert result_01.sample_size_per_group > result_05.sample_size_per_group
    
    def test_sensitivity_analysis_included(self):
        """Test that sensitivity analysis is generated"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert result.sensitivity_analysis is not None
        assert "by_effect_size" in result.sensitivity_analysis
        assert "by_power_level" in result.sensitivity_analysis
        assert len(result.sensitivity_analysis["by_effect_size"]) > 0
    
    def test_interpretation_generated(self):
        """Test that interpretation text is generated"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert len(result.interpretation) > 0
        assert "80%" in result.interpretation or "0.80" in result.interpretation
    
    def test_to_dict_serialization(self):
        """Test JSON-serializable output"""
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "test_type" in d
        assert "results" in d
        assert "parameters" in d
        assert d["results"]["sample_size_per_group"] is not None
    
    def test_invalid_alpha(self):
        """Test error handling for invalid alpha"""
        with pytest.raises(ValueError, match="alpha"):
            TTestPowerAnalysis.calculate_sample_size(
                effect_size=0.5,
                alpha=1.5,  # Invalid
                power=0.80,
            )
    
    def test_invalid_power(self):
        """Test error handling for invalid power"""
        with pytest.raises(ValueError, match="power"):
            TTestPowerAnalysis.calculate_sample_size(
                effect_size=0.5,
                alpha=0.05,
                power=1.2,  # Invalid
            )
    
    def test_zero_effect_size(self):
        """Test error handling for zero effect size"""
        with pytest.raises(ValueError, match="effect_size"):
            TTestPowerAnalysis.calculate_sample_size(
                effect_size=0.0,
                alpha=0.05,
                power=0.80,
            )
    
    def test_missing_parameters(self):
        """Test error when neither effect_size nor means provided"""
        with pytest.raises(ValueError):
            TTestPowerAnalysis.calculate_sample_size(
                alpha=0.05,
                power=0.80,
            )


class TestTTestPower:
    """Tests for t-test power calculation"""
    
    def test_power_calculation_basic(self):
        """Test basic power calculation"""
        result = TTestPowerAnalysis.calculate_power(
            n=64,
            effect_size=0.5,
            alpha=0.05,
            test_type="two-sample",
        )
        
        assert result.scenario == "power"
        assert result.power is not None
        assert 0.75 < result.power < 0.85  # Should be around 80%
    
    def test_power_increases_with_n(self):
        """Test that power increases with sample size"""
        result_small = TTestPowerAnalysis.calculate_power(
            n=30,
            effect_size=0.5,
            alpha=0.05,
            test_type="two-sample",
        )
        
        result_large = TTestPowerAnalysis.calculate_power(
            n=100,
            effect_size=0.5,
            alpha=0.05,
            test_type="two-sample",
        )
        
        assert result_large.power > result_small.power
    
    def test_power_increases_with_effect_size(self):
        """Test that power increases with effect size"""
        result_small = TTestPowerAnalysis.calculate_power(
            n=50,
            effect_size=0.3,
            alpha=0.05,
            test_type="two-sample",
        )
        
        result_large = TTestPowerAnalysis.calculate_power(
            n=50,
            effect_size=0.7,
            alpha=0.05,
            test_type="two-sample",
        )
        
        assert result_large.power > result_small.power
    
    def test_power_from_means(self):
        """Test power calculation from means and SD"""
        result = TTestPowerAnalysis.calculate_power(
            n=64,
            mean1=105,
            mean2=100,
            sd=10,
            alpha=0.05,
            test_type="two-sample",
        )
        
        assert result.power is not None
        assert result.effect_size == pytest.approx(0.5, rel=0.01)
    
    def test_power_paired(self):
        """Test power for paired t-test"""
        result = TTestPowerAnalysis.calculate_power(
            n=30,
            effect_size=0.5,
            alpha=0.05,
            test_type="paired",
        )
        
        assert result.test_type == "paired t-test"
        assert result.power > 0.7  # Paired tests have good power


# =============================================================================
# Proportion Test Power Analysis Tests
# =============================================================================

class TestProportionSampleSize:
    """Tests for proportion test sample size calculation"""
    
    def test_two_proportions_basic(self):
        """Test two-proportions sample size calculation"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert result.test_type == "two proportions test"
        assert result.sample_size_per_group is not None
        assert result.sample_size_per_group > 0
        assert result.p1 == 0.50
        assert result.p2 == 0.70
    
    def test_two_proportions_small_difference(self):
        """Test with small proportion difference"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.55,  # Small difference
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Small difference needs large sample
        assert result.sample_size_per_group > 500
    
    def test_two_proportions_large_difference(self):
        """Test with large proportion difference"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.30,
            p2=0.70,  # Large difference
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Large difference needs smaller sample
        assert result.sample_size_per_group < 50
    
    def test_clinical_trial_scenario(self):
        """Test typical clinical trial scenario"""
        # New drug 70% vs old drug 50% effective
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # statsmodels uses normal approximation, yields ~93 per group
        assert 80 < result.sample_size_per_group < 110
        assert "NNT" in str(result.recommendations)  # Should mention NNT
    
    def test_unequal_allocation(self):
        """Test with unequal group allocation"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
            ratio=2.0,
            test_type="two-sample",
        )
        
        assert result.ratio == 2.0
    
    def test_one_proportion(self):
        """Test one-proportion sample size calculation"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.60,  # Observed/expected proportion
            p0=0.50,  # Hypothesized proportion
            alpha=0.05,
            power=0.80,
            test_type="one-sample",
        )
        
        assert result.test_type == "one proportion test"
        assert result.sample_size_per_group == result.total_sample_size
    
    def test_extreme_proportions_warning(self):
        """Test warning for extreme proportions"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.02,  # Very low proportion
            p2=0.10,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Should have warning about extreme proportions
        assert any("extreme" in r.lower() for r in result.recommendations)
    
    def test_effect_size_cohens_h(self):
        """Test that Cohen's h is correctly calculated"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.30,
            p2=0.50,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert result.effect_size_type == "Cohen's h"
        assert result.effect_size is not None
    
    def test_sensitivity_analysis(self):
        """Test sensitivity analysis for proportions"""
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert result.sensitivity_analysis is not None
        assert "by_power_level" in result.sensitivity_analysis
    
    def test_missing_p2_for_two_sample(self):
        """Test error when p2 missing for two-sample test"""
        with pytest.raises(ValueError, match="p2"):
            ProportionPowerAnalysis.calculate_sample_size(
                p1=0.50,
                alpha=0.05,
                power=0.80,
                test_type="two-sample",
            )
    
    def test_missing_p0_for_one_sample(self):
        """Test error when p0 missing for one-sample test"""
        with pytest.raises(ValueError, match="p0"):
            ProportionPowerAnalysis.calculate_sample_size(
                p1=0.60,
                alpha=0.05,
                power=0.80,
                test_type="one-sample",
            )
    
    def test_invalid_proportion(self):
        """Test error for invalid proportion"""
        with pytest.raises(ValueError, match="p1"):
            ProportionPowerAnalysis.calculate_sample_size(
                p1=1.5,  # Invalid
                p2=0.50,
                alpha=0.05,
                power=0.80,
            )


class TestProportionPower:
    """Tests for proportion test power calculation"""
    
    def test_power_calculation_basic(self):
        """Test basic power calculation for proportions"""
        result = ProportionPowerAnalysis.calculate_power(
            n=64,
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            test_type="two-sample",
        )
        
        assert result.scenario == "power"
        assert result.power is not None
        # With n=64, power is ~64% for this effect size
        assert 0.5 < result.power < 0.8
    
    def test_power_increases_with_n(self):
        """Test that power increases with sample size"""
        result_small = ProportionPowerAnalysis.calculate_power(
            n=30,
            p1=0.50,
            p2=0.70,
            alpha=0.05,
        )
        
        result_large = ProportionPowerAnalysis.calculate_power(
            n=100,
            p1=0.50,
            p2=0.70,
            alpha=0.05,
        )
        
        assert result_large.power > result_small.power
    
    def test_power_one_sample(self):
        """Test power for one-sample proportion test"""
        result = ProportionPowerAnalysis.calculate_power(
            n=100,
            p1=0.60,
            p0=0.50,
            alpha=0.05,
            test_type="one-sample",
        )
        
        assert result.test_type == "one proportion test"
        # Small effect (d=0.2) with n=100 gives ~30% power
        assert result.power > 0.2


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for MCP-friendly wrapper functions"""
    
    def test_calculate_ttest_sample_size(self):
        """Test t-test sample size convenience function"""
        result = calculate_ttest_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        assert isinstance(result, dict)
        assert "results" in result
        assert result["results"]["sample_size_per_group"] is not None
    
    def test_calculate_ttest_sample_size_from_means(self):
        """Test t-test sample size from means"""
        result = calculate_ttest_sample_size(
            mean1=105,
            mean2=100,
            sd=10,
            power=0.80,
        )
        
        assert isinstance(result, dict)
        assert result["parameters"]["mean1"] == 105
    
    def test_calculate_ttest_power(self):
        """Test t-test power convenience function"""
        result = calculate_ttest_power(
            n=64,
            effect_size=0.5,
            alpha=0.05,
        )
        
        assert isinstance(result, dict)
        assert result["results"]["power"] is not None
    
    def test_calculate_proportion_sample_size(self):
        """Test proportion sample size convenience function"""
        result = calculate_proportion_sample_size(
            p1=0.50,
            p2=0.70,
            power=0.80,
        )
        
        assert isinstance(result, dict)
        assert result["results"]["sample_size_per_group"] is not None
    
    def test_calculate_proportion_power(self):
        """Test proportion power convenience function"""
        result = calculate_proportion_power(
            n=64,
            p1=0.50,
            p2=0.70,
        )
        
        assert isinstance(result, dict)
        assert result["results"]["power"] is not None


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests verifying consistency"""
    
    def test_sample_size_power_consistency(self):
        """Test that calculated sample size achieves target power"""
        # First, calculate required sample size for 80% power
        ss_result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Then verify power with that sample size
        power_result = TTestPowerAnalysis.calculate_power(
            n=ss_result.sample_size_per_group,
            effect_size=0.5,
            alpha=0.05,
            test_type="two-sample",
        )
        
        # Power should be at least 80%
        assert power_result.power >= 0.79  # Allow small rounding tolerance
    
    def test_proportion_consistency(self):
        """Test consistency for proportion tests"""
        # Calculate sample size
        ss_result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
        )
        
        # Verify power
        power_result = ProportionPowerAnalysis.calculate_power(
            n=ss_result.sample_size_per_group,
            p1=0.50,
            p2=0.70,
            alpha=0.05,
        )
        
        assert power_result.power >= 0.79
    
    def test_known_values_ttest(self):
        """Test against known values from literature"""
        # Cohen's table: d=0.5, alpha=0.05, power=0.80 → n≈64 per group
        result = TTestPowerAnalysis.calculate_sample_size(
            effect_size=0.5,
            alpha=0.05,
            power=0.80,
            test_type="two-sample",
        )
        
        # Allow 10% tolerance from Cohen's tables
        assert 58 <= result.sample_size_per_group <= 70
    
    def test_known_values_proportion(self):
        """Test proportion calculation against known values"""
        # 50% vs 70% with standard parameters
        result = ProportionPowerAnalysis.calculate_sample_size(
            p1=0.50,
            p2=0.70,
            alpha=0.05,
            power=0.80,
        )
        
        # statsmodels normal approximation: ~93 per group
        assert 85 <= result.sample_size_per_group <= 100

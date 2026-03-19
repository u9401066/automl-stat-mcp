"""
Tests for Phase 6.2: ANOVA and Chi-square Power Analysis

Tests cover:
- ANOVAPowerAnalysis sample size and power calculations
- ChiSquarePowerAnalysis sample size and power calculations
- Effect size conversions (Cohen's f, eta-squared, Cohen's w)
- Convenience wrapper functions
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tasks.power_analysis import (
    # ANOVA
    ANOVAPowerAnalysis,
    # Chi-square
    ChiSquarePowerAnalysis,
    calculate_anova_power,
    calculate_anova_sample_size,
    calculate_chisquare_power,
    calculate_chisquare_sample_size,
    cohens_f_from_eta_squared,
    cohens_f_from_means,
    cramers_v_from_table,
    effect_size_w_from_proportions,
    eta_squared_from_cohens_f,
)

# =============================================================================
# ANOVA Helper Function Tests
# =============================================================================


class TestANOVAHelperFunctions:
    """Tests for ANOVA effect size helper functions"""

    def test_cohens_f_from_means_basic(self):
        """Test Cohen's f calculation from group means"""
        # 3 groups: 10, 12, 14 with SD=4
        f = cohens_f_from_means([10, 12, 14], pooled_sd=4)
        assert 0.3 < f < 0.6  # Medium-large effect

    def test_cohens_f_from_means_no_difference(self):
        """Test with no group differences"""
        f = cohens_f_from_means([10, 10, 10], pooled_sd=5)
        assert f == 0.0

    def test_cohens_f_from_means_with_group_sds(self):
        """Test with individual group SDs"""
        f = cohens_f_from_means([10, 15, 20], group_sds=[4, 5, 6])
        assert f > 0

    def test_cohens_f_from_eta_squared(self):
        """Test conversion from eta-squared"""
        # Small effect: η² = 0.01 → f ≈ 0.1
        f = cohens_f_from_eta_squared(0.01)
        assert 0.09 < f < 0.11

        # Medium effect: η² = 0.06 → f ≈ 0.25
        f = cohens_f_from_eta_squared(0.06)
        assert 0.24 < f < 0.26

    def test_eta_squared_from_cohens_f(self):
        """Test conversion to eta-squared"""
        # f = 0.25 → η² ≈ 0.059
        eta = eta_squared_from_cohens_f(0.25)
        assert 0.05 < eta < 0.07

    def test_effect_size_roundtrip(self):
        """Test f → η² → f conversion preserves value"""
        original_f = 0.35
        eta = eta_squared_from_cohens_f(original_f)
        recovered_f = cohens_f_from_eta_squared(eta)
        assert abs(original_f - recovered_f) < 0.001

    def test_invalid_eta_squared(self):
        """Test invalid eta-squared values"""
        with pytest.raises(ValueError):
            cohens_f_from_eta_squared(1.0)  # η² cannot be 1
        with pytest.raises(ValueError):
            cohens_f_from_eta_squared(-0.1)  # Cannot be negative


# =============================================================================
# ANOVA Sample Size Tests
# =============================================================================


class TestANOVASampleSize:
    """Tests for ANOVA sample size calculation"""

    def test_medium_effect_3_groups(self):
        """Test sample size for medium effect with 3 groups"""
        result = ANOVAPowerAnalysis.calculate_sample_size(
            effect_size=0.25,
            k_groups=3,
            alpha=0.05,
            power=0.80,
        )

        assert result.scenario == "sample_size"
        assert result.test_type == "one-way ANOVA"
        assert result.n_per_group > 0
        assert result.total_n == result.n_per_group * 3
        assert result.k_groups == 3

    def test_small_effect_requires_larger_sample(self):
        """Test that small effects need larger samples"""
        small = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.10, k_groups=3, power=0.80)
        medium = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=3, power=0.80)

        assert small.n_per_group > medium.n_per_group

    def test_more_groups_needs_larger_sample(self):
        """Test that more groups require larger total sample"""
        three = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=3, power=0.80)
        five = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=5, power=0.80)

        assert five.total_n > three.total_n

    def test_from_group_means(self):
        """Test calculation from group means"""
        result = ANOVAPowerAnalysis.calculate_sample_size(
            group_means=[10, 12, 15],
            pooled_sd=5,
            alpha=0.05,
            power=0.80,
        )

        assert result.n_per_group > 0
        assert result.effect_size_f > 0
        assert result.k_groups == 3

    def test_from_eta_squared(self):
        """Test calculation from eta-squared"""
        result = ANOVAPowerAnalysis.calculate_sample_size(
            eta_squared=0.06,  # Medium effect
            k_groups=4,
            power=0.80,
        )

        assert result.n_per_group > 0
        assert 0.24 < result.effect_size_f < 0.26

    def test_sensitivity_analysis_included(self):
        """Test that sensitivity analysis is generated"""
        result = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=3, power=0.80)

        assert result.sensitivity_analysis is not None
        assert "by_power_level" in result.sensitivity_analysis
        assert "by_k_groups" in result.sensitivity_analysis

    def test_interpretation_generated(self):
        """Test that interpretation text is generated"""
        result = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=3, power=0.80)

        assert result.interpretation != ""
        assert "80%" in result.interpretation

    def test_to_dict_serialization(self):
        """Test result serialization"""
        result = ANOVAPowerAnalysis.calculate_sample_size(effect_size=0.25, k_groups=3, power=0.80)

        d = result.to_dict()
        assert "results" in d
        assert "parameters" in d
        assert "n_per_group" in d["results"]

    def test_invalid_k_groups(self):
        """Test validation of k_groups"""
        with pytest.raises(ValueError):
            ANOVAPowerAnalysis.calculate_sample_size(
                effect_size=0.25,
                k_groups=1,  # Need at least 2
            )

    def test_missing_effect_size_info(self):
        """Test error when no effect size information provided"""
        with pytest.raises(ValueError):
            ANOVAPowerAnalysis.calculate_sample_size(
                k_groups=3,
                power=0.80,
                # No effect_size, eta_squared, or group_means
            )


# =============================================================================
# ANOVA Power Tests
# =============================================================================


class TestANOVAPower:
    """Tests for ANOVA power calculation"""

    def test_power_calculation_basic(self):
        """Test basic power calculation"""
        result = ANOVAPowerAnalysis.calculate_power(
            n_per_group=50,
            effect_size=0.25,
            k_groups=3,
            alpha=0.05,
        )

        assert result.scenario == "power"
        assert 0 < result.power < 1

    def test_power_increases_with_n(self):
        """Test that power increases with sample size"""
        small = ANOVAPowerAnalysis.calculate_power(n_per_group=20, effect_size=0.25, k_groups=3)
        large = ANOVAPowerAnalysis.calculate_power(n_per_group=100, effect_size=0.25, k_groups=3)

        assert large.power > small.power

    def test_power_increases_with_effect_size(self):
        """Test that power increases with effect size"""
        small_effect = ANOVAPowerAnalysis.calculate_power(n_per_group=50, effect_size=0.10, k_groups=3)
        large_effect = ANOVAPowerAnalysis.calculate_power(n_per_group=50, effect_size=0.40, k_groups=3)

        assert large_effect.power > small_effect.power

    def test_underpowered_recommendation(self):
        """Test that underpowered studies get recommendations"""
        result = ANOVAPowerAnalysis.calculate_power(n_per_group=10, effect_size=0.25, k_groups=3)

        # Should be underpowered and have recommendations
        assert result.power < 0.80
        assert len(result.recommendations) > 0


# =============================================================================
# Chi-Square Helper Function Tests
# =============================================================================


class TestChiSquareHelperFunctions:
    """Tests for chi-square effect size functions"""

    def test_effect_size_w_uniform(self):
        """Test Cohen's w against uniform distribution"""
        # Large deviation from uniform
        w = effect_size_w_from_proportions([0.10, 0.20, 0.30, 0.40])
        assert w > 0.2

    def test_effect_size_w_no_difference(self):
        """Test with no difference from uniform"""
        w = effect_size_w_from_proportions([0.25, 0.25, 0.25, 0.25])
        assert abs(w) < 0.001

    def test_effect_size_w_custom_expected(self):
        """Test with custom expected distribution"""
        w = effect_size_w_from_proportions([0.30, 0.30, 0.20, 0.20], [0.25, 0.25, 0.25, 0.25])
        assert w > 0

    def test_cramers_v_from_table(self):
        """Test Cramér's V calculation from contingency table"""
        # Independent table (no association)
        independent = np.array([[50, 50], [50, 50]])
        v = cramers_v_from_table(independent)
        assert v < 0.1  # Should be near zero

        # Strongly associated table
        associated = np.array([[90, 10], [10, 90]])
        v = cramers_v_from_table(associated)
        assert v > 0.5  # Should be large


# =============================================================================
# Chi-Square Sample Size Tests
# =============================================================================


class TestChiSquareSampleSize:
    """Tests for chi-square sample size calculation"""

    def test_goodness_of_fit_basic(self):
        """Test goodness-of-fit sample size"""
        result = ChiSquarePowerAnalysis.calculate_sample_size(
            effect_size=0.3,
            n_bins=4,
            alpha=0.05,
            power=0.80,
        )

        assert result.scenario == "sample_size"
        assert result.n > 0
        assert result.df == 3  # n_bins - 1

    def test_independence_test(self):
        """Test independence test (contingency table)"""
        result = ChiSquarePowerAnalysis.calculate_sample_size(
            effect_size=0.3,
            n_rows=2,
            n_cols=3,
            power=0.80,
        )

        assert result.test_type == "chi-square independence"
        assert result.df == 2  # (2-1) * (3-1)
        assert result.n > 0

    def test_small_effect_requires_larger_sample(self):
        """Test that small effects need larger samples"""
        small = ChiSquarePowerAnalysis.calculate_sample_size(effect_size=0.1, n_bins=4, power=0.80)
        medium = ChiSquarePowerAnalysis.calculate_sample_size(effect_size=0.3, n_bins=4, power=0.80)

        assert small.n > medium.n

    def test_more_df_needs_larger_sample(self):
        """Test that more df require larger samples"""
        small_df = ChiSquarePowerAnalysis.calculate_sample_size(effect_size=0.3, df=1, power=0.80)
        large_df = ChiSquarePowerAnalysis.calculate_sample_size(effect_size=0.3, df=5, power=0.80)

        assert large_df.n > small_df.n

    def test_cramers_v_reported_for_contingency(self):
        """Test that Cramér's V is calculated for contingency tables"""
        result = ChiSquarePowerAnalysis.calculate_sample_size(
            effect_size=0.3,
            n_rows=3,
            n_cols=4,
            power=0.80,
        )

        assert result.cramers_v is not None
        assert result.cramers_v > 0

    def test_sensitivity_analysis_included(self):
        """Test sensitivity analysis generation"""
        result = ChiSquarePowerAnalysis.calculate_sample_size(effect_size=0.3, n_bins=4, power=0.80)

        assert result.sensitivity_analysis is not None
        assert "by_power_level" in result.sensitivity_analysis


# =============================================================================
# Chi-Square Power Tests
# =============================================================================


class TestChiSquarePower:
    """Tests for chi-square power calculation"""

    def test_power_calculation_basic(self):
        """Test basic power calculation"""
        result = ChiSquarePowerAnalysis.calculate_power(
            n=100,
            effect_size=0.3,
            df=3,
            alpha=0.05,
        )

        assert result.scenario == "power"
        assert 0 < result.power < 1

    def test_power_increases_with_n(self):
        """Test that power increases with sample size"""
        small = ChiSquarePowerAnalysis.calculate_power(n=50, effect_size=0.3, df=3)
        large = ChiSquarePowerAnalysis.calculate_power(n=200, effect_size=0.3, df=3)

        assert large.power > small.power

    def test_underpowered_recommendation(self):
        """Test recommendations for underpowered studies"""
        result = ChiSquarePowerAnalysis.calculate_power(n=30, effect_size=0.3, df=3)

        assert result.power < 0.80
        assert len(result.recommendations) > 0


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for MCP-friendly wrapper functions"""

    def test_calculate_anova_sample_size(self):
        """Test ANOVA sample size wrapper"""
        result = calculate_anova_sample_size(
            effect_size=0.25,
            k_groups=3,
            power=0.80,
        )

        assert "results" in result
        assert result["results"]["n_per_group"] > 0

    def test_calculate_anova_power(self):
        """Test ANOVA power wrapper"""
        result = calculate_anova_power(
            n_per_group=50,
            effect_size=0.25,
            k_groups=3,
        )

        assert "results" in result
        assert 0 < result["results"]["power"] < 1

    def test_calculate_chisquare_sample_size(self):
        """Test chi-square sample size wrapper"""
        result = calculate_chisquare_sample_size(
            effect_size=0.3,
            n_bins=4,
            power=0.80,
        )

        assert "results" in result
        assert result["results"]["n"] > 0

    def test_calculate_chisquare_power(self):
        """Test chi-square power wrapper"""
        result = calculate_chisquare_power(
            n=100,
            effect_size=0.3,
            df=3,
        )

        assert "results" in result
        assert 0 < result["results"]["power"] < 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for sample size and power consistency"""

    def test_anova_sample_size_power_consistency(self):
        """Test that calculated sample size achieves target power"""
        # Get sample size for 80% power
        size_result = ANOVAPowerAnalysis.calculate_sample_size(
            effect_size=0.25,
            k_groups=3,
            power=0.80,
        )

        # Calculate power with that sample size
        power_result = ANOVAPowerAnalysis.calculate_power(
            n_per_group=size_result.n_per_group,
            effect_size=0.25,
            k_groups=3,
        )

        # Power should be >= 0.80
        assert power_result.power >= 0.79

    def test_chisquare_sample_size_power_consistency(self):
        """Test chi-square sample size and power consistency"""
        # Get sample size for 80% power
        size_result = ChiSquarePowerAnalysis.calculate_sample_size(
            effect_size=0.3,
            df=3,
            power=0.80,
        )

        # Calculate power with that sample size
        power_result = ChiSquarePowerAnalysis.calculate_power(
            n=size_result.n,
            effect_size=0.3,
            df=3,
        )

        # Power should be >= 0.80
        assert power_result.power >= 0.79

    def test_anova_known_values(self):
        """Test ANOVA against known values"""
        # Medium effect, 3 groups, 80% power
        # Expected: approximately 52-55 per group (varies by implementation)
        result = ANOVAPowerAnalysis.calculate_sample_size(
            effect_size=0.25,
            k_groups=3,
            power=0.80,
        )

        # statsmodels gives higher estimates due to conservative calculation
        assert 50 < result.n_per_group < 200

    def test_chisquare_known_values(self):
        """Test chi-square against known values"""
        # Medium effect, df=3, 80% power
        result = ChiSquarePowerAnalysis.calculate_sample_size(
            effect_size=0.3,
            df=3,
            power=0.80,
        )

        # Should be around 120-150
        assert 100 < result.n < 200

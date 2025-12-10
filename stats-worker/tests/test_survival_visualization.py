"""
Tests for Survival Visualization Module - Phase 8B

Tests covering:
- Kaplan-Meier curve plotting
- Cumulative hazard plotting
- Forest plot for Cox regression
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, '/home/eric/workspace251204/stats-worker/src')

from visualization.survival import (
    plot_kaplan_meier,
    plot_cumulative_hazard,
    plot_forest_plot,
    plot_hazard_ratio,
    create_survival_visualizations,
    _make_step_curve,
    _get_at_risk_at_time,
)
from visualization.schemas import VisualizationType


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def km_result_single():
    """Single group KM result."""
    return {
        "group": "Overall",
        "n_subjects": 100,
        "n_events": 45,
        "n_censored": 55,
        "median_survival": 24.5,
        "median_ci": {"lower": 20.0, "upper": 30.0},
        "survival_curve": [
            {"time": 0, "survival": 1.0, "ci_lower": 1.0, "ci_upper": 1.0, "at_risk": 100, "events": 0, "censored": 0},
            {"time": 6, "survival": 0.92, "ci_lower": 0.86, "ci_upper": 0.96, "at_risk": 95, "events": 5, "censored": 3},
            {"time": 12, "survival": 0.78, "ci_lower": 0.70, "ci_upper": 0.85, "at_risk": 80, "events": 10, "censored": 5},
            {"time": 18, "survival": 0.62, "ci_lower": 0.52, "ci_upper": 0.71, "at_risk": 60, "events": 12, "censored": 8},
            {"time": 24, "survival": 0.48, "ci_lower": 0.37, "ci_upper": 0.58, "at_risk": 42, "events": 10, "censored": 8},
            {"time": 30, "survival": 0.35, "ci_lower": 0.25, "ci_upper": 0.46, "at_risk": 28, "events": 8, "censored": 6},
        ]
    }


@pytest.fixture
def km_results_two_groups():
    """Two group KM results for comparison."""
    return [
        {
            "group": "Treatment",
            "n_subjects": 50,
            "n_events": 18,
            "n_censored": 32,
            "median_survival": 32.0,
            "survival_curve": [
                {"time": 0, "survival": 1.0, "ci_lower": 1.0, "ci_upper": 1.0, "at_risk": 50, "events": 0, "censored": 0},
                {"time": 6, "survival": 0.96, "ci_lower": 0.88, "ci_upper": 0.99, "at_risk": 48, "events": 2, "censored": 1},
                {"time": 12, "survival": 0.88, "ci_lower": 0.77, "ci_upper": 0.94, "at_risk": 42, "events": 4, "censored": 2},
                {"time": 24, "survival": 0.72, "ci_lower": 0.58, "ci_upper": 0.83, "at_risk": 32, "events": 6, "censored": 4},
                {"time": 36, "survival": 0.58, "ci_lower": 0.42, "ci_upper": 0.72, "at_risk": 22, "events": 6, "censored": 4},
            ]
        },
        {
            "group": "Control",
            "n_subjects": 50,
            "n_events": 27,
            "n_censored": 23,
            "median_survival": 18.0,
            "survival_curve": [
                {"time": 0, "survival": 1.0, "ci_lower": 1.0, "ci_upper": 1.0, "at_risk": 50, "events": 0, "censored": 0},
                {"time": 6, "survival": 0.88, "ci_lower": 0.77, "ci_upper": 0.94, "at_risk": 44, "events": 6, "censored": 2},
                {"time": 12, "survival": 0.68, "ci_lower": 0.54, "ci_upper": 0.79, "at_risk": 34, "events": 8, "censored": 2},
                {"time": 24, "survival": 0.42, "ci_lower": 0.28, "ci_upper": 0.55, "at_risk": 20, "events": 10, "censored": 4},
                {"time": 36, "survival": 0.28, "ci_lower": 0.15, "ci_upper": 0.42, "at_risk": 12, "events": 3, "censored": 5},
            ]
        }
    ]


@pytest.fixture
def cox_result():
    """Cox regression result."""
    return {
        "n_subjects": 100,
        "n_events": 45,
        "coefficients": [
            {
                "variable": "age",
                "coefficient": 0.035,
                "std_error": 0.012,
                "hazard_ratio": 1.036,
                "hr_ci": {"lower": 1.012, "upper": 1.060},
                "z_score": 2.92,
                "p_value": 0.004,
                "significant": True
            },
            {
                "variable": "treatment",
                "coefficient": -0.62,
                "std_error": 0.24,
                "hazard_ratio": 0.538,
                "hr_ci": {"lower": 0.336, "upper": 0.861},
                "z_score": -2.58,
                "p_value": 0.01,
                "significant": True
            },
            {
                "variable": "stage",
                "coefficient": 0.18,
                "std_error": 0.15,
                "hazard_ratio": 1.197,
                "hr_ci": {"lower": 0.891, "upper": 1.608},
                "z_score": 1.20,
                "p_value": 0.23,
                "significant": False
            },
        ],
        "model_fit": {
            "log_likelihood": -185.3,
            "log_likelihood_null": -198.5,
            "concordance": 0.68,
        },
        "global_tests": {
            "likelihood_ratio": {"statistic": 26.4, "p_value": 0.0001},
            "wald": {"statistic": 24.2, "p_value": 0.0002},
        }
    }


# =============================================================================
# Unit Tests - Helper Functions
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_make_step_curve_empty(self):
        """Test step curve with empty data."""
        times, values = _make_step_curve([], [])
        assert times == []
        assert values == []
    
    def test_make_step_curve_single_point(self):
        """Test step curve with single point."""
        times, values = _make_step_curve([0], [1.0])
        assert len(times) == 1
        assert len(values) == 1
    
    def test_make_step_curve_multiple_points(self):
        """Test step curve with multiple points."""
        times, values = _make_step_curve([0, 6, 12], [1.0, 0.9, 0.8])
        # Should create step function coordinates
        assert len(times) > 3  # Step function has more points
        assert times[0] == 0
        assert values[0] == 1.0
    
    def test_get_at_risk_at_time(self):
        """Test at risk calculation at specific times."""
        curve_data = [
            {"time": 0, "at_risk": 100},
            {"time": 6, "at_risk": 90},
            {"time": 12, "at_risk": 75},
        ]
        
        assert _get_at_risk_at_time(curve_data, 0) == 100
        assert _get_at_risk_at_time(curve_data, 3) == 100  # Before first change
        assert _get_at_risk_at_time(curve_data, 6) == 100  # At time 6, use previous
        assert _get_at_risk_at_time(curve_data, 10) == 90
        assert _get_at_risk_at_time(curve_data, 20) == 75  # After last point
    
    def test_get_at_risk_empty(self):
        """Test at risk with empty data."""
        assert _get_at_risk_at_time([], 5) == 0


# =============================================================================
# Unit Tests - Kaplan-Meier Plot
# =============================================================================

class TestKaplanMeierPlot:
    """Tests for Kaplan-Meier plotting."""
    
    def test_plot_single_group(self, km_result_single):
        """Test plotting single KM curve."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(km_result_single)
        
        assert fig is not None
        assert len(fig.axes) >= 1  # At least main axis
        
        plt.close(fig)
    
    def test_plot_two_groups(self, km_results_two_groups):
        """Test plotting two-group comparison."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(km_results_two_groups)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_with_log_rank_p(self, km_results_two_groups):
        """Test plotting with log-rank p-value."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(km_results_two_groups, log_rank_p=0.003)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_without_ci(self, km_result_single):
        """Test plotting without confidence intervals."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(km_result_single, show_ci=False)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_without_risk_table(self, km_result_single):
        """Test plotting without at-risk table."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(km_result_single, show_at_risk=False)
        
        assert fig is not None
        assert len(fig.axes) == 1  # Only main axis
        
        plt.close(fig)
    
    def test_plot_custom_colors(self, km_results_two_groups):
        """Test plotting with custom colors."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(
            km_results_two_groups,
            colors=['#FF0000', '#0000FF']
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_custom_title(self, km_result_single):
        """Test plotting with custom title."""
        import matplotlib.pyplot as plt
        
        fig = plot_kaplan_meier(
            km_result_single,
            title="Progression-Free Survival",
            xlabel="Months",
            ylabel="PFS Probability"
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Cumulative Hazard Plot
# =============================================================================

class TestCumulativeHazardPlot:
    """Tests for cumulative hazard plotting."""
    
    def test_plot_single_group(self, km_result_single):
        """Test cumulative hazard for single group."""
        import matplotlib.pyplot as plt
        
        fig = plot_cumulative_hazard(km_result_single)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_two_groups(self, km_results_two_groups):
        """Test cumulative hazard for two groups."""
        import matplotlib.pyplot as plt
        
        fig = plot_cumulative_hazard(km_results_two_groups)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_without_ci(self, km_result_single):
        """Test without confidence intervals."""
        import matplotlib.pyplot as plt
        
        fig = plot_cumulative_hazard(km_result_single, show_ci=False)
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Forest Plot
# =============================================================================

class TestForestPlot:
    """Tests for forest plot."""
    
    def test_plot_forest(self, cox_result):
        """Test basic forest plot."""
        import matplotlib.pyplot as plt
        
        fig = plot_forest_plot(cox_result)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_forest_empty_coefficients(self):
        """Test forest plot with no coefficients."""
        import matplotlib.pyplot as plt
        
        fig = plot_forest_plot({"coefficients": []})
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_forest_sorted_by_hr(self, cox_result):
        """Test forest plot sorted by HR."""
        import matplotlib.pyplot as plt
        
        fig = plot_forest_plot(cox_result, sort_by='hr')
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_forest_sorted_by_pvalue(self, cox_result):
        """Test forest plot sorted by p-value."""
        import matplotlib.pyplot as plt
        
        fig = plot_forest_plot(cox_result, sort_by='pvalue')
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_forest_linear_scale(self, cox_result):
        """Test forest plot with linear scale."""
        import matplotlib.pyplot as plt
        
        fig = plot_forest_plot(cox_result, log_scale=False)
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Hazard Ratio Plot
# =============================================================================

class TestHazardRatioPlot:
    """Tests for single hazard ratio plot."""
    
    def test_plot_significant_higher_risk(self):
        """Test HR > 1 significantly."""
        import matplotlib.pyplot as plt
        
        fig = plot_hazard_ratio(
            hr=1.8,
            ci_lower=1.2,
            ci_upper=2.7,
            label="Treatment Effect"
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_significant_lower_risk(self):
        """Test HR < 1 significantly."""
        import matplotlib.pyplot as plt
        
        fig = plot_hazard_ratio(
            hr=0.5,
            ci_lower=0.3,
            ci_upper=0.8,
            label="Protective Effect"
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_plot_not_significant(self):
        """Test HR crossing 1."""
        import matplotlib.pyplot as plt
        
        fig = plot_hazard_ratio(
            hr=1.2,
            ci_lower=0.8,
            ci_upper=1.8,
            label="No Significant Effect"
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Integration Tests
# =============================================================================

class TestCreateSurvivalVisualizations:
    """Tests for high-level visualization creation."""
    
    @patch('visualization.survival.save_figure_to_minio')
    def test_create_visualizations_km_only(self, mock_save, km_results_two_groups):
        """Test creating visualizations with KM data only."""
        mock_save.return_value = "https://minio.example.com/test.png"
        
        # Convert to dict format
        km_dict = {
            "groups": {
                "Treatment": km_results_two_groups[0],
                "Control": km_results_two_groups[1],
            }
        }
        
        results = create_survival_visualizations(
            km_dict,
            log_rank_p=0.02,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )
        
        assert len(results) >= 2  # KM + cumulative hazard
        
        # Check types
        types = [r.type for r in results]
        assert VisualizationType.KAPLAN_MEIER in types
        assert VisualizationType.CUMULATIVE_HAZARD in types
    
    @patch('visualization.survival.save_figure_to_minio')
    def test_create_visualizations_with_cox(self, mock_save, km_results_two_groups, cox_result):
        """Test creating visualizations with KM and Cox data."""
        mock_save.return_value = "https://minio.example.com/test.png"
        
        km_dict = {
            "groups": {
                "Treatment": km_results_two_groups[0],
                "Control": km_results_two_groups[1],
            }
        }
        
        results = create_survival_visualizations(
            km_dict,
            cox_result=cox_result,
            log_rank_p=0.02,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )
        
        assert len(results) >= 3  # KM + cumulative hazard + forest
        
        types = [r.type for r in results]
        assert VisualizationType.FOREST_PLOT in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

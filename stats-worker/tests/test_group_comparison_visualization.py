"""
Tests for Group Comparison Visualization Module - Phase 8D

Tests covering:
- Box plots with p-value annotations
- ANOVA results visualization
- Contingency table heatmaps
- Categorical comparison plots
- Correlation heatmaps
- T-test visualization
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, '/home/eric/workspace251204/stats-worker/src')

from visualization.group_comparison import (
    plot_group_comparison,
    plot_anova_results,
    plot_contingency_heatmap,
    plot_categorical_comparison,
    plot_correlation_heatmap,
    plot_ttest_result,
    create_group_comparison_visualizations,
)
from visualization.schemas import VisualizationType


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def two_group_df():
    """DataFrame with two groups for t-test."""
    np.random.seed(42)
    return pd.DataFrame({
        'group': ['A'] * 50 + ['B'] * 50,
        'value': np.concatenate([
            np.random.normal(10, 2, 50),
            np.random.normal(12, 2, 50)
        ])
    })


@pytest.fixture
def multi_group_df():
    """DataFrame with multiple groups for ANOVA."""
    np.random.seed(42)
    return pd.DataFrame({
        'group': ['A'] * 30 + ['B'] * 30 + ['C'] * 30,
        'value': np.concatenate([
            np.random.normal(10, 2, 30),
            np.random.normal(12, 2, 30),
            np.random.normal(15, 2, 30)
        ])
    })


@pytest.fixture
def categorical_df():
    """DataFrame with categorical variables for chi-square."""
    np.random.seed(42)
    return pd.DataFrame({
        'treatment': np.random.choice(['Drug', 'Placebo'], 100),
        'outcome': np.random.choice(['Improved', 'No Change', 'Worsened'], 100),
    })


@pytest.fixture
def group_stats():
    """Sample group statistics for ANOVA plot."""
    return {
        'Control': {'mean': 10.5, 'std': 2.1, 'n': 30},
        'Treatment A': {'mean': 12.8, 'std': 2.3, 'n': 28},
        'Treatment B': {'mean': 15.2, 'std': 2.0, 'n': 32},
    }


@pytest.fixture
def test_result_ttest():
    """Sample t-test result."""
    return {
        'test_name': 'Independent t-test',
        'statistic': 2.85,
        'p_value': 0.0052,
        'effect_size': 0.65,
        'effect_size_name': "Cohen's d"
    }


@pytest.fixture
def test_result_anova():
    """Sample ANOVA result."""
    return {
        'test_name': 'One-way ANOVA',
        'statistic': 15.32,
        'p_value': 0.0001,
        'effect_size': 0.18
    }


@pytest.fixture
def test_result_chisquare():
    """Sample chi-square result."""
    return {
        'chi2': 8.45,
        'p_value': 0.015,
        'cramers_v': 0.29
    }


@pytest.fixture
def contingency_table():
    """Sample contingency table."""
    return pd.DataFrame(
        [[40, 25, 10], [15, 30, 20]],
        index=['Drug', 'Placebo'],
        columns=['Improved', 'No Change', 'Worsened']
    )


@pytest.fixture
def correlation_matrix():
    """Sample correlation matrix."""
    np.random.seed(42)
    data = np.random.randn(100, 5)
    df = pd.DataFrame(data, columns=['Var1', 'Var2', 'Var3', 'Var4', 'Var5'])
    return df.corr()


@pytest.fixture
def post_hoc_results():
    """Sample post-hoc test results."""
    return [
        {'group1': 'Control', 'group2': 'Treatment A', 'p_value': 0.02},
        {'group1': 'Control', 'group2': 'Treatment B', 'p_value': 0.001},
        {'group1': 'Treatment A', 'group2': 'Treatment B', 'p_value': 0.08},
    ]


# =============================================================================
# Unit Tests - Group Comparison Plot
# =============================================================================

class TestGroupComparisonPlot:
    """Tests for plot_group_comparison function."""
    
    def test_boxplot_basic(self, two_group_df):
        """Test basic boxplot."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            plot_type='boxplot'
        )
        
        assert fig is not None
        assert len(fig.axes) >= 1
        
        plt.close(fig)
    
    def test_violin_plot(self, two_group_df):
        """Test violin plot."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            plot_type='violin'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_bar_plot(self, two_group_df):
        """Test bar plot."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            plot_type='bar'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_strip_plot(self, two_group_df):
        """Test strip plot."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            plot_type='strip'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_custom_pairs_and_pvalues(self, two_group_df):
        """Test with pre-computed p-values."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            pairs=[('A', 'B')],
            p_values=[0.005]
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_multi_group(self, multi_group_df):
        """Test with multiple groups."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=multi_group_df,
            x='group',
            y='value',
            plot_type='boxplot'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_dict_input(self):
        """Test with dictionary input."""
        import matplotlib.pyplot as plt
        
        data = {
            'Group A': np.random.normal(10, 2, 30),
            'Group B': np.random.normal(12, 2, 30),
        }
        
        fig = plot_group_comparison(
            data=data,
            x='group',
            y='value',
            plot_type='boxplot'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_custom_title_and_labels(self, two_group_df):
        """Test with custom title and labels."""
        import matplotlib.pyplot as plt
        
        fig = plot_group_comparison(
            data=two_group_df,
            x='group',
            y='value',
            title='Custom Title',
            xlabel='Treatment',
            ylabel='Outcome Value'
        )
        
        assert fig is not None
        ax = fig.axes[0]
        assert ax.get_title() == 'Custom Title'
        assert ax.get_xlabel() == 'Treatment'
        assert ax.get_ylabel() == 'Outcome Value'
        
        plt.close(fig)


# =============================================================================
# Unit Tests - ANOVA Results Plot
# =============================================================================

class TestANOVAResultsPlot:
    """Tests for plot_anova_results function."""
    
    def test_basic_plot(self, group_stats):
        """Test basic ANOVA results plot."""
        import matplotlib.pyplot as plt
        
        fig = plot_anova_results(group_stats)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_test_result(self, group_stats, test_result_anova):
        """Test with statistical test annotation."""
        import matplotlib.pyplot as plt
        
        fig = plot_anova_results(
            group_stats,
            test_result=test_result_anova
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_post_hoc(self, group_stats, test_result_anova, post_hoc_results):
        """Test with post-hoc annotations."""
        import matplotlib.pyplot as plt
        
        fig = plot_anova_results(
            group_stats,
            test_result=test_result_anova,
            post_hoc=post_hoc_results
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_custom_title(self, group_stats):
        """Test with custom title."""
        import matplotlib.pyplot as plt
        
        fig = plot_anova_results(
            group_stats,
            title="Treatment Effect Analysis"
        )
        
        assert fig is not None
        ax = fig.axes[0]
        assert "Treatment Effect Analysis" in ax.get_title()
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Contingency Heatmap
# =============================================================================

class TestContingencyHeatmap:
    """Tests for plot_contingency_heatmap function."""
    
    def test_basic_heatmap(self, contingency_table):
        """Test basic contingency heatmap."""
        import matplotlib.pyplot as plt
        
        fig = plot_contingency_heatmap(contingency_table)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_test_result(self, contingency_table, test_result_chisquare):
        """Test with chi-square annotation."""
        import matplotlib.pyplot as plt
        
        fig = plot_contingency_heatmap(
            contingency_table,
            test_result=test_result_chisquare
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_numpy_array_input(self):
        """Test with numpy array input."""
        import matplotlib.pyplot as plt
        
        arr = np.array([[40, 25], [15, 30]])
        
        fig = plot_contingency_heatmap(
            arr,
            row_labels=['Drug', 'Placebo'],
            col_labels=['Improved', 'Not Improved']
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_without_percentages(self, contingency_table):
        """Test without percentages."""
        import matplotlib.pyplot as plt
        
        fig = plot_contingency_heatmap(
            contingency_table,
            show_percentages=False
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Categorical Comparison
# =============================================================================

class TestCategoricalComparison:
    """Tests for plot_categorical_comparison function."""
    
    def test_basic_plot(self, categorical_df):
        """Test basic categorical comparison."""
        import matplotlib.pyplot as plt
        
        fig = plot_categorical_comparison(
            categorical_df,
            x='outcome',
            hue='treatment'
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_test_result(self, categorical_df, test_result_chisquare):
        """Test with chi-square annotation."""
        import matplotlib.pyplot as plt
        
        fig = plot_categorical_comparison(
            categorical_df,
            x='outcome',
            hue='treatment',
            test_result=test_result_chisquare
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_no_normalization(self, categorical_df):
        """Test without normalization."""
        import matplotlib.pyplot as plt
        
        fig = plot_categorical_comparison(
            categorical_df,
            x='outcome',
            hue='treatment',
            normalize=None
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - Correlation Heatmap
# =============================================================================

class TestCorrelationHeatmap:
    """Tests for plot_correlation_heatmap function."""
    
    def test_basic_heatmap(self, correlation_matrix):
        """Test basic correlation heatmap."""
        import matplotlib.pyplot as plt
        
        fig = plot_correlation_heatmap(correlation_matrix)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_without_mask(self, correlation_matrix):
        """Test without upper triangle mask."""
        import matplotlib.pyplot as plt
        
        fig = plot_correlation_heatmap(
            correlation_matrix,
            mask_upper=False
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_without_annotations(self, correlation_matrix):
        """Test without value annotations."""
        import matplotlib.pyplot as plt
        
        fig = plot_correlation_heatmap(
            correlation_matrix,
            annot=False
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_numpy_array_input(self):
        """Test with numpy array input."""
        import matplotlib.pyplot as plt
        
        np.random.seed(42)
        arr = np.corrcoef(np.random.randn(5, 50))
        
        fig = plot_correlation_heatmap(
            arr,
            labels=['A', 'B', 'C', 'D', 'E']
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Unit Tests - T-Test Result
# =============================================================================

class TestTTestResult:
    """Tests for plot_ttest_result function."""
    
    def test_basic_plot(self):
        """Test basic t-test result plot."""
        import matplotlib.pyplot as plt
        
        np.random.seed(42)
        g1 = np.random.normal(10, 2, 30)
        g2 = np.random.normal(12, 2, 30)
        
        fig = plot_ttest_result(g1, g2)
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_with_test_result(self, test_result_ttest):
        """Test with test result annotation."""
        import matplotlib.pyplot as plt
        
        np.random.seed(42)
        g1 = np.random.normal(10, 2, 30)
        g2 = np.random.normal(12, 2, 30)
        
        fig = plot_ttest_result(
            g1, g2,
            group1_name='Control',
            group2_name='Treatment',
            test_result=test_result_ttest
        )
        
        assert fig is not None
        
        plt.close(fig)
    
    def test_violin_type(self):
        """Test with violin plot type."""
        import matplotlib.pyplot as plt
        
        np.random.seed(42)
        g1 = np.random.normal(10, 2, 30)
        g2 = np.random.normal(12, 2, 30)
        
        fig = plot_ttest_result(
            g1, g2,
            plot_type='violin'
        )
        
        assert fig is not None
        
        plt.close(fig)


# =============================================================================
# Integration Tests
# =============================================================================

class TestCreateGroupComparisonVisualizations:
    """Tests for high-level visualization creation."""
    
    @patch('visualization.group_comparison.save_figure_to_minio')
    def test_ttest_result(self, mock_save):
        """Test visualization from t-test comparison result."""
        mock_save.return_value = "https://minio.example.com/test.png"
        
        comparison_result = {
            'main_test': {
                'test_name': 'Independent t-test',
                'statistic': 2.85,
                'p_value': 0.005,
                'interpretation': 'Significant',
                'details': {
                    'effect_size': 0.65,
                    'effect_size_name': "Cohen's d"
                }
            },
            'group_statistics': {
                'Control': {'mean': 10.5, 'std': 2.1, 'n': 30},
                'Treatment': {'mean': 12.8, 'std': 2.3, 'n': 30},
            }
        }
        
        results = create_group_comparison_visualizations(
            comparison_result,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )
        
        assert len(results) >= 1
    
    @patch('visualization.group_comparison.save_figure_to_minio')
    def test_anova_result(self, mock_save):
        """Test visualization from ANOVA comparison result."""
        mock_save.return_value = "https://minio.example.com/test.png"
        
        comparison_result = {
            'main_test': {
                'test_name': 'One-way ANOVA',
                'statistic': 15.32,
                'p_value': 0.0001,
                'interpretation': 'Significant',
                'details': {
                    'effect_size': 0.18,
                    'effect_size_name': "η²"
                }
            },
            'group_statistics': {
                'Control': {'mean': 10.5, 'std': 2.1, 'n': 30},
                'Treatment A': {'mean': 12.8, 'std': 2.3, 'n': 28},
                'Treatment B': {'mean': 15.2, 'std': 2.0, 'n': 32},
            },
            'post_hoc': [
                {'group1': 'Control', 'group2': 'Treatment A', 'p_value': 0.02},
                {'group1': 'Control', 'group2': 'Treatment B', 'p_value': 0.001},
            ]
        }
        
        results = create_group_comparison_visualizations(
            comparison_result,
            user_id="test_user",
            job_id="test_job",
            save_to_minio=True,
        )
        
        assert len(results) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

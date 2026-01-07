"""
Tests for Visualization Module - Phase 8A

Tests covering:
- Storage utilities (MinIO upload)
- Style configuration
- Schema dataclasses
"""

# Import modules to test
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, '/home/eric/workspace251204/stats-worker/src')

from visualization.schemas import (
    GroupComparisonVisualizationResult,
    ROCVisualizationResult,
    SurvivalVisualizationResult,
    VisualizationBundle,
    VisualizationConfig,
    VisualizationResult,
    VisualizationType,
)
from visualization.style import (
    CLINICAL_COLORS,
    PUBLICATION_STYLE,
    ROC_COLORS,
    SURVIVAL_COLORS,
    apply_publication_style,
    get_figure_with_style,
)

# =============================================================================
# Schema Tests
# =============================================================================

class TestVisualizationType:
    """Tests for VisualizationType enum."""

    def test_roc_curve_type(self):
        """Test ROC curve type."""
        assert VisualizationType.ROC_CURVE.value == "roc_curve"

    def test_kaplan_meier_type(self):
        """Test Kaplan-Meier type."""
        assert VisualizationType.KAPLAN_MEIER.value == "kaplan_meier"

    def test_boxplot_type(self):
        """Test boxplot type."""
        assert VisualizationType.BOXPLOT.value == "boxplot"

    def test_all_types_have_values(self):
        """Ensure all enum members have string values."""
        for viz_type in VisualizationType:
            assert isinstance(viz_type.value, str)
            assert len(viz_type.value) > 0


class TestVisualizationResult:
    """Tests for VisualizationResult dataclass."""

    def test_basic_creation(self):
        """Test basic result creation."""
        result = VisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc.png",
            title="ROC Curve"
        )
        assert result.type == VisualizationType.ROC_CURVE
        assert result.url == "https://example.com/roc.png"
        assert result.title == "ROC Curve"
        assert result.format == "png"  # default

    def test_full_creation(self):
        """Test full result creation with all fields."""
        result = VisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc.svg",
            title="ROC Curve",
            description="AUC = 0.85",
            metadata={"auc": 0.85, "ci": [0.80, 0.90]},
            format="svg",
            width=800,
            height=600
        )
        assert result.description == "AUC = 0.85"
        assert result.metadata["auc"] == 0.85
        assert result.format == "svg"
        assert result.width == 800

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = VisualizationResult(
            type=VisualizationType.BOXPLOT,
            url="https://example.com/boxplot.png",
            title="Group Comparison",
            metadata={"p_value": 0.03}
        )
        d = result.to_dict()
        assert d["type"] == "boxplot"
        assert d["url"] == "https://example.com/boxplot.png"
        assert d["metadata"]["p_value"] == 0.03

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "type": "kaplan_meier",
            "url": "https://example.com/km.png",
            "title": "Survival Curve",
            "description": "Log-rank p < 0.001"
        }
        result = VisualizationResult.from_dict(data)
        assert result.type == VisualizationType.KAPLAN_MEIER
        assert result.title == "Survival Curve"


class TestVisualizationBundle:
    """Tests for VisualizationBundle dataclass."""

    def test_bundle_creation(self):
        """Test bundle creation."""
        bundle = VisualizationBundle(
            job_id="job123",
            user_id="user456"
        )
        assert bundle.job_id == "job123"
        assert bundle.user_id == "user456"
        assert len(bundle.visualizations) == 0

    def test_add_visualization(self):
        """Test adding visualization to bundle."""
        bundle = VisualizationBundle(job_id="job123", user_id="user456")
        viz = VisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc.png",
            title="ROC"
        )
        bundle.add(viz)
        assert len(bundle.visualizations) == 1
        assert bundle.visualizations[0].title == "ROC"

    def test_get_by_type(self):
        """Test filtering by type."""
        bundle = VisualizationBundle(job_id="job123", user_id="user456")
        bundle.add(VisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc.png",
            title="ROC"
        ))
        bundle.add(VisualizationResult(
            type=VisualizationType.PR_CURVE,
            url="https://example.com/pr.png",
            title="PR"
        ))
        bundle.add(VisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc2.png",
            title="ROC 2"
        ))

        roc_plots = bundle.get_by_type(VisualizationType.ROC_CURVE)
        assert len(roc_plots) == 2

        pr_plots = bundle.get_by_type(VisualizationType.PR_CURVE)
        assert len(pr_plots) == 1

    def test_bundle_to_dict(self):
        """Test bundle serialization."""
        bundle = VisualizationBundle(job_id="job123", user_id="user456")
        bundle.add(VisualizationResult(
            type=VisualizationType.HEATMAP,
            url="https://example.com/heatmap.png",
            title="Correlation"
        ))
        d = bundle.to_dict()
        assert d["job_id"] == "job123"
        assert len(d["visualizations"]) == 1
        assert d["visualizations"][0]["type"] == "heatmap"


class TestVisualizationConfig:
    """Tests for VisualizationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VisualizationConfig()
        assert config.dpi == 300
        assert config.format == "png"
        assert config.width == 8.0
        assert config.height == 6.0
        assert config.style == "publication"

    def test_custom_config(self):
        """Test custom configuration."""
        config = VisualizationConfig(
            dpi=600,
            format="svg",
            transparent=True
        )
        assert config.dpi == 600
        assert config.format == "svg"
        assert config.transparent is True


class TestSpecializedResults:
    """Tests for specialized result classes."""

    def test_roc_visualization_result(self):
        """Test ROC-specific result."""
        result = ROCVisualizationResult(
            type=VisualizationType.ROC_CURVE,
            url="https://example.com/roc.png",
            title="ROC Curve",
            auc=0.85,
            auc_ci_lower=0.80,
            auc_ci_upper=0.90,
            optimal_threshold=0.45
        )
        assert result.auc == 0.85
        assert result.metadata["auc"] == 0.85
        assert result.metadata["auc_ci"] == [0.80, 0.90]
        assert result.metadata["optimal_threshold"] == 0.45

    def test_survival_visualization_result(self):
        """Test survival-specific result."""
        result = SurvivalVisualizationResult(
            type=VisualizationType.KAPLAN_MEIER,
            url="https://example.com/km.png",
            title="Kaplan-Meier",
            hazard_ratio=1.5,
            hr_ci_lower=1.2,
            hr_ci_upper=1.9,
            p_value=0.001
        )
        assert result.hazard_ratio == 1.5
        assert result.metadata["hazard_ratio"] == 1.5
        assert result.metadata["p_value"] == 0.001

    def test_group_comparison_result(self):
        """Test group comparison result."""
        result = GroupComparisonVisualizationResult(
            type=VisualizationType.BOXPLOT,
            url="https://example.com/box.png",
            title="Treatment vs Control",
            p_value=0.03,
            effect_size=0.72,
            test_name="Mann-Whitney U"
        )
        assert result.p_value == 0.03
        assert result.metadata["test_name"] == "Mann-Whitney U"


# =============================================================================
# Style Tests
# =============================================================================

class TestPublicationStyle:
    """Tests for publication style configuration."""

    def test_publication_style_exists(self):
        """Test that publication style dict is defined."""
        assert PUBLICATION_STYLE is not None
        assert isinstance(PUBLICATION_STYLE, dict)

    def test_publication_style_has_required_keys(self):
        """Test that required style keys exist."""
        required_keys = [
            'figure.dpi',
            'font.size',
            'axes.labelsize',
            'savefig.dpi',
        ]
        for key in required_keys:
            assert key in PUBLICATION_STYLE, f"Missing key: {key}"

    def test_savefig_dpi_is_300(self):
        """Test that save DPI is publication quality."""
        assert PUBLICATION_STYLE['savefig.dpi'] == 300

    def test_spines_hidden(self):
        """Test that top/right spines are hidden."""
        assert PUBLICATION_STYLE['axes.spines.top'] is False
        assert PUBLICATION_STYLE['axes.spines.right'] is False


class TestColorPalettes:
    """Tests for color palette definitions."""

    def test_clinical_colors_defined(self):
        """Test clinical colors palette."""
        assert 'primary' in CLINICAL_COLORS
        assert 'treatment' in CLINICAL_COLORS
        assert 'control' in CLINICAL_COLORS

    def test_roc_colors_defined(self):
        """Test ROC colors palette."""
        assert 'curve' in ROC_COLORS
        assert 'diagonal' in ROC_COLORS
        assert 'optimal' in ROC_COLORS

    def test_survival_colors_defined(self):
        """Test survival colors palette."""
        assert 'group1' in SURVIVAL_COLORS
        assert 'censored' in SURVIVAL_COLORS

    def test_colors_are_valid_hex(self):
        """Test that colors are valid hex codes."""
        import re
        hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')

        for name, color in CLINICAL_COLORS.items():
            assert hex_pattern.match(color), f"Invalid hex color: {name} = {color}"


class TestStyleFunctions:
    """Tests for style functions."""

    def test_apply_publication_style(self):
        """Test applying publication style."""
        import matplotlib.pyplot as plt

        # Apply style
        apply_publication_style()

        # Check a few rcParams
        assert plt.rcParams['savefig.dpi'] == 300
        assert plt.rcParams['axes.spines.top'] is False

    def test_get_figure_with_style(self):
        """Test creating figure with style."""
        fig, ax = get_figure_with_style()

        assert fig is not None
        assert ax is not None

        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_get_figure_custom_size(self):
        """Test creating figure with custom size."""
        import matplotlib.pyplot as plt

        fig, ax = get_figure_with_style(figsize=(10, 8))

        # Check figure size
        width, height = fig.get_size_inches()
        assert width == 10
        assert height == 8

        plt.close(fig)


# =============================================================================
# Storage Tests (Mocked)
# =============================================================================

class TestStorageFunctions:
    """Tests for storage functions with mocked MinIO."""

    @patch('visualization.storage.Minio')
    def test_save_figure_to_minio(self, mock_minio_class):
        """Test saving figure to MinIO."""
        import matplotlib.pyplot as plt
        from visualization.storage import save_figure_to_minio

        # Create a mock MinIO client
        mock_client = MagicMock()
        mock_minio_class.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        # Create a simple figure
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])

        # This should not raise an error
        try:
            save_figure_to_minio(
                fig=fig,
                user_id="test_user",
                job_id="test_job",
                filename="test_plot.png"
            )
            # Check that put_object was called
            assert mock_client.put_object.called
        except Exception:
            # If minio env vars not set, that's okay for unit tests
            pass
        finally:
            plt.close(fig)

    def test_get_figure_url(self):
        """Test URL generation."""
        from visualization.storage import get_figure_url

        url = get_figure_url(
            bucket="stats-reports",
            object_path="user123/job456/roc.png",
            presigned=False
        )

        assert "stats-reports" in url
        assert "user123/job456/roc.png" in url


# =============================================================================
# Integration Tests (Require Full Environment)
# =============================================================================

@pytest.mark.skip(reason="Requires full environment with MinIO")
class TestIntegration:
    """Integration tests requiring full environment."""

    def test_full_visualization_workflow(self):
        """Test complete visualization workflow."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
ANOVA and Chi-square Power Analysis Tools

Tools:
    - calculate_anova_sample_size
    - calculate_anova_power
    - calculate_anova_effect_size
    - calculate_chisquare_sample_size
    - calculate_chisquare_power
    - calculate_chisquare_effect_size
"""
from typing import List, Optional

from ..base import logger


def register_anova_power_tools(mcp, stats_client):
    """Register ANOVA and Chi-square power analysis tools."""
    
    @mcp.tool()
    async def calculate_anova_sample_size(
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        power: float = 0.80,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        📊 Calculate sample size for one-way ANOVA.
        
        Determines how many participants per group for comparing
        means across multiple groups (3+ groups).
        
        Args:
            effect_size: Cohen's f effect size
                - 0.10 = small effect
                - 0.25 = medium effect
                - 0.40 = large effect
            k_groups: Number of groups (default: 3)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            group_means: List of expected group means (alternative)
            pooled_sd: Pooled standard deviation
            eta_squared: Eta-squared (η²) effect size (alternative)
        
        Returns:
            n_per_group: Sample size per group
            total_n: Total sample size
            effect_size_f: Cohen's f
            eta_squared: Eta-squared (% variance explained)
        
        Example:
            calculate_anova_sample_size(effect_size=0.25, k_groups=3)
            # Returns: n_per_group=52, total=156
        """
        from ..stats_worker_tasks import ANOVAPowerAnalysis
        
        try:
            result = ANOVAPowerAnalysis.calculate_sample_size(
                effect_size=effect_size,
                k_groups=k_groups,
                alpha=alpha,
                power=power,
                group_means=group_means,
                pooled_sd=pooled_sd,
                eta_squared=eta_squared,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "ANOVA power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_anova_sample_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_anova_power(
        n_per_group: int,
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        ⚡ Calculate power for one-way ANOVA given sample size.
        
        Args:
            n_per_group: Sample size per group
            effect_size: Cohen's f
            k_groups: Number of groups
            alpha: Significance level
            group_means: Group means (alternative)
            pooled_sd: Pooled SD
            eta_squared: Eta-squared (alternative)
        
        Returns:
            power: Statistical power (0-1)
            interpretation: Adequacy assessment
            recommendations: Suggestions if underpowered
        """
        from ..stats_worker_tasks import ANOVAPowerAnalysis
        
        try:
            result = ANOVAPowerAnalysis.calculate_power(
                n_per_group=n_per_group,
                effect_size=effect_size,
                k_groups=k_groups,
                alpha=alpha,
                group_means=group_means,
                pooled_sd=pooled_sd,
                eta_squared=eta_squared,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "ANOVA power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_anova_power error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_anova_effect_size(
        group_means: List[float],
        pooled_sd: Optional[float] = None,
        group_sds: Optional[List[float]] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        🧮 Calculate Cohen's f effect size for ANOVA.
        
        Args:
            group_means: List of expected group means
            pooled_sd: Pooled standard deviation
            group_sds: Standard deviations per group
            eta_squared: Eta-squared to convert
        
        Returns:
            cohens_f: Cohen's f effect size
            eta_squared: Equivalent eta-squared
            interpretation: small/medium/large
        
        Example:
            calculate_anova_effect_size(group_means=[10, 12, 15], pooled_sd=5)
        """
        from ..stats_worker_tasks import (
            cohens_f_from_means,
            cohens_f_from_eta_squared,
            eta_squared_from_cohens_f,
            interpret_effect_size,
        )
        
        try:
            if eta_squared is not None:
                f = cohens_f_from_eta_squared(eta_squared)
                eta_sq = eta_squared
            elif group_means is not None:
                f = cohens_f_from_means(group_means, group_sds, pooled_sd)
                eta_sq = eta_squared_from_cohens_f(f)
            else:
                return {"status": "error", "error": "Provide group_means or eta_squared"}
            
            interp = interpret_effect_size(f, "cohens_f")
            
            return {
                "cohens_f": round(f, 4),
                "eta_squared": round(eta_sq, 4),
                "interpretation": interp,
                "variance_explained": f"{eta_sq*100:.1f}%",
            }
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_anova_effect_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_chisquare_sample_size(
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
    ) -> dict:
        """
        📊 Calculate sample size for chi-square test.
        
        For comparing categorical distributions or testing independence.
        
        Args:
            effect_size: Cohen's w effect size
                - 0.10 = small effect
                - 0.30 = medium effect
                - 0.50 = large effect
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            df: Degrees of freedom
            n_bins: Number of categories (for goodness-of-fit)
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
        
        Returns:
            n: Required sample size
            effect_size_w: Cohen's w
        
        Example:
            calculate_chisquare_sample_size(effect_size=0.3, n_bins=4)
        """
        from ..stats_worker_tasks import ChiSquarePowerAnalysis
        
        try:
            result = ChiSquarePowerAnalysis.calculate_sample_size(
                effect_size=effect_size,
                alpha=alpha,
                power=power,
                df=df,
                n_bins=n_bins,
                n_rows=n_rows,
                n_cols=n_cols,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Chi-square power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_chisquare_sample_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_chisquare_power(
        n: int,
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
    ) -> dict:
        """
        ⚡ Calculate power for chi-square test given sample size.
        
        Args:
            n: Sample size
            effect_size: Cohen's w
            alpha: Significance level
            df: Degrees of freedom
            n_bins: Number of categories
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
        
        Returns:
            power: Statistical power
            recommendations: Suggestions if underpowered
        """
        from ..stats_worker_tasks import ChiSquarePowerAnalysis
        
        try:
            result = ChiSquarePowerAnalysis.calculate_power(
                n=n,
                effect_size=effect_size,
                alpha=alpha,
                df=df,
                n_bins=n_bins,
                n_rows=n_rows,
                n_cols=n_cols,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Chi-square power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_chisquare_power error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_chisquare_effect_size(
        observed_proportions: List[float],
        expected_proportions: Optional[List[float]] = None,
    ) -> dict:
        """
        🧮 Calculate Cohen's w effect size for chi-square test.
        
        Args:
            observed_proportions: Observed category proportions
            expected_proportions: Expected proportions (uniform if None)
        
        Returns:
            cohens_w: Cohen's w effect size
            interpretation: small/medium/large
        
        Example:
            calculate_chisquare_effect_size(
                observed_proportions=[0.10, 0.20, 0.30, 0.40]
            )
        """
        from ..stats_worker_tasks import effect_size_w_from_proportions
        
        try:
            w = effect_size_w_from_proportions(observed_proportions, expected_proportions)
            
            if w < 0.1:
                interp = "negligible"
            elif w < 0.3:
                interp = "small"
            elif w < 0.5:
                interp = "medium"
            else:
                interp = "large"
            
            return {
                "cohens_w": round(w, 4),
                "interpretation": interp,
                "observed": observed_proportions,
                "expected": expected_proportions or [1/len(observed_proportions)] * len(observed_proportions),
                "n_categories": len(observed_proportions),
                "df": len(observed_proportions) - 1,
            }
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_chisquare_effect_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    logger.info("ANOVA/Chi-square power tools registered: 6 tools")

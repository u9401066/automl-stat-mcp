"""
Chi-Square Power Analysis Module

Power analysis for chi-square tests.

Contains:
    - ChiSquarePowerResult: Result dataclass for chi-square power calculations
    - ChiSquarePowerAnalysis: Main analysis class
    - Helper functions for effect size calculation
    - Convenience wrapper functions for MCP tools
"""
import logging
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import numpy as np
from scipy import stats
from statsmodels.stats.power import GofChisquarePower

from .base import safe_round

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions for Chi-Square
# =============================================================================

def cramers_v_from_table(observed: np.ndarray) -> float:
    """
    Calculate Cramér's V from a contingency table.
    
    Cramér's V = sqrt(χ² / (n * min(r-1, c-1)))
    
    Args:
        observed: Contingency table (2D array)
        
    Returns:
        Cramér's V effect size
    """
    chi2, p, dof, expected = stats.chi2_contingency(observed)
    n = np.sum(observed)
    min_dim = min(observed.shape) - 1
    
    if n * min_dim == 0:
        return 0.0
    
    return math.sqrt(chi2 / (n * min_dim))


def effect_size_w_from_proportions(
    p_observed: List[float],
    p_expected: Optional[List[float]] = None,
) -> float:
    """
    Calculate Cohen's w effect size for chi-square test.
    
    w = sqrt(sum((p_obs - p_exp)² / p_exp))
    
    Args:
        p_observed: Observed proportions
        p_expected: Expected proportions (uniform if None)
        
    Returns:
        Cohen's w effect size
    """
    p_obs = np.array(p_observed)
    
    if p_expected is None:
        # Uniform distribution
        k = len(p_obs)
        p_exp = np.ones(k) / k
    else:
        p_exp = np.array(p_expected)
    
    # Normalize to sum to 1
    p_obs = p_obs / np.sum(p_obs)
    p_exp = p_exp / np.sum(p_exp)
    
    # Avoid division by zero
    p_exp = np.maximum(p_exp, 1e-10)
    
    w = math.sqrt(np.sum((p_obs - p_exp)**2 / p_exp))
    return w


# =============================================================================
# Result Dataclass
# =============================================================================

@dataclass
class ChiSquarePowerResult:
    """Result of chi-square power analysis"""
    
    test_type: str = "chi-square goodness-of-fit"
    scenario: str = "sample_size"
    
    # Results
    n: Optional[int] = None
    power: Optional[float] = None
    
    # Parameters
    effect_size_w: Optional[float] = None
    df: int = 1  # degrees of freedom
    alpha: float = 0.05
    n_bins: Optional[int] = None  # for goodness-of-fit
    
    # For contingency table
    n_rows: Optional[int] = None
    n_cols: Optional[int] = None
    cramers_v: Optional[float] = None
    
    # Interpretation
    effect_size_interpretation: str = "medium"
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    method: str = "statsmodels GofChisquarePower"
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_type": self.test_type,
            "scenario": self.scenario,
            "results": {
                "n": self.n,
                "power": safe_round(self.power, 4),
            },
            "parameters": {
                "effect_size_w": safe_round(self.effect_size_w, 4),
                "cramers_v": safe_round(self.cramers_v, 4),
                "df": self.df,
                "alpha": self.alpha,
                "n_bins": self.n_bins,
                "n_rows": self.n_rows,
                "n_cols": self.n_cols,
            },
            "effect_size_interpretation": self.effect_size_interpretation,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "sensitivity_analysis": self.sensitivity_analysis,
            "method": self.method,
            "notes": self.notes,
        }


# =============================================================================
# Chi-Square Power Analysis Class
# =============================================================================

class ChiSquarePowerAnalysis:
    """
    Power analysis for chi-square tests.
    
    Supports:
    - Goodness-of-fit test (one variable)
    - Test of independence (contingency table)
    
    Effect size conventions (Cohen's w):
    - Small: 0.10
    - Medium: 0.30
    - Large: 0.50
    
    Note: Cohen's w is related to Cramér's V by:
    w = V * sqrt(min(r-1, c-1)) for contingency tables
    """
    
    @staticmethod
    def calculate_sample_size(
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
        p_observed: Optional[List[float]] = None,
        p_expected: Optional[List[float]] = None,
    ) -> ChiSquarePowerResult:
        """
        Calculate sample size for chi-square test.
        
        Args:
            effect_size: Cohen's w effect size
            alpha: Significance level
            power: Desired power
            df: Degrees of freedom (calculated if not provided)
            n_bins: Number of categories for goodness-of-fit
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
            p_observed: Observed proportions (to calculate w)
            p_expected: Expected proportions
            
        Returns:
            ChiSquarePowerResult with sample size
        """
        # Determine test type and df
        test_type = "chi-square goodness-of-fit"
        
        if n_rows is not None and n_cols is not None:
            test_type = "chi-square independence"
            if df is None:
                df = (n_rows - 1) * (n_cols - 1)
        elif n_bins is not None:
            if df is None:
                df = n_bins - 1
        elif df is None:
            df = 1  # Default
        
        # Calculate effect size if not provided
        if effect_size is None:
            if p_observed is not None:
                effect_size = effect_size_w_from_proportions(p_observed, p_expected)
                if n_bins is None:
                    n_bins = len(p_observed)
                if df is None:
                    df = n_bins - 1
            else:
                raise ValueError(
                    "Provide effect_size (Cohen's w) or p_observed proportions"
                )
        
        # Calculate sample size
        chi2_power = GofChisquarePower()
        n = chi2_power.solve_power(
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            n_bins=df + 1,  # GofChisquarePower uses n_bins
        )
        
        n = int(math.ceil(n))
        
        # Effect size interpretation (same as Cohen's d convention roughly)
        if effect_size < 0.1:
            interp = "negligible"
        elif effect_size < 0.3:
            interp = "small"
        elif effect_size < 0.5:
            interp = "medium"
        else:
            interp = "large"
        
        # Cramér's V for contingency tables
        cramers_v = None
        if n_rows is not None and n_cols is not None:
            min_dim = min(n_rows - 1, n_cols - 1)
            if min_dim > 0:
                cramers_v = effect_size / math.sqrt(min_dim)
        
        # Sensitivity analysis
        sensitivity = ChiSquarePowerAnalysis._sensitivity_analysis(
            effect_size=effect_size,
            df=df,
            alpha=alpha,
        )
        
        # Interpretation
        interp_text = (
            f"To detect an effect (Cohen's w = {effect_size:.3f}) with "
            f"{power*100:.0f}% power at α = {alpha} (df = {df}), "
            f"you need N = {n}."
        )
        
        recs = []
        if interp == "small":
            recs.append("Small effect size requires large sample. Ensure effect is meaningful.")
        if df > 10:
            recs.append(f"With df = {df}, consider collapsing categories if possible.")
        if cramers_v is not None:
            recs.append(f"Cramér's V ≈ {cramers_v:.3f} for effect interpretation in contingency table.")
        
        return ChiSquarePowerResult(
            test_type=test_type,
            scenario="sample_size",
            n=n,
            power=power,
            effect_size_w=effect_size,
            df=df,
            alpha=alpha,
            n_bins=n_bins,
            n_rows=n_rows,
            n_cols=n_cols,
            cramers_v=cramers_v,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
            sensitivity_analysis=sensitivity,
        )
    
    @staticmethod
    def calculate_power(
        n: int,
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
        p_observed: Optional[List[float]] = None,
        p_expected: Optional[List[float]] = None,
    ) -> ChiSquarePowerResult:
        """
        Calculate power for chi-square test given sample size.
        
        Args:
            n: Sample size
            effect_size: Cohen's w
            alpha: Significance level
            df: Degrees of freedom
            n_bins: Number of categories
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table
            p_observed: Observed proportions
            p_expected: Expected proportions
            
        Returns:
            ChiSquarePowerResult with power
        """
        # Determine test type and df
        test_type = "chi-square goodness-of-fit"
        
        if n_rows is not None and n_cols is not None:
            test_type = "chi-square independence"
            if df is None:
                df = (n_rows - 1) * (n_cols - 1)
        elif n_bins is not None:
            if df is None:
                df = n_bins - 1
        elif df is None:
            df = 1
        
        # Calculate effect size if needed
        if effect_size is None:
            if p_observed is not None:
                effect_size = effect_size_w_from_proportions(p_observed, p_expected)
                if n_bins is None:
                    n_bins = len(p_observed)
                if df is None:
                    df = n_bins - 1
            else:
                raise ValueError("Provide effect_size or p_observed")
        
        # Calculate power
        chi2_power = GofChisquarePower()
        power = chi2_power.solve_power(
            effect_size=effect_size,
            nobs=n,
            alpha=alpha,
            n_bins=df + 1,
        )
        
        # Effect size interpretation
        if effect_size < 0.1:
            interp = "negligible"
        elif effect_size < 0.3:
            interp = "small"
        elif effect_size < 0.5:
            interp = "medium"
        else:
            interp = "large"
        
        # Cramér's V
        cramers_v = None
        if n_rows is not None and n_cols is not None:
            min_dim = min(n_rows - 1, n_cols - 1)
            if min_dim > 0:
                cramers_v = effect_size / math.sqrt(min_dim)
        
        interp_text = (
            f"With N = {n}, effect size w = {effect_size:.3f}, df = {df}, "
            f"the study has {power*100:.1f}% power at α = {alpha}."
        )
        
        recs = []
        if power < 0.80:
            needed_n = ChiSquarePowerAnalysis.calculate_sample_size(
                effect_size=effect_size,
                alpha=alpha,
                power=0.80,
                df=df,
            ).n
            recs.append(f"Power is {power*100:.1f}%. Need N = {needed_n} for 80% power.")
        
        return ChiSquarePowerResult(
            test_type=test_type,
            scenario="power",
            n=n,
            power=power,
            effect_size_w=effect_size,
            df=df,
            alpha=alpha,
            n_bins=n_bins,
            n_rows=n_rows,
            n_cols=n_cols,
            cramers_v=cramers_v,
            effect_size_interpretation=interp,
            interpretation=interp_text,
            recommendations=recs,
        )
    
    @staticmethod
    def _sensitivity_analysis(
        effect_size: float,
        df: int,
        alpha: float,
        power_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate sensitivity analysis for chi-square"""
        if power_range is None:
            power_range = [0.70, 0.80, 0.85, 0.90, 0.95]
        
        chi2_power = GofChisquarePower()
        
        by_power = []
        for pwr in power_range:
            n = chi2_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=pwr,
                n_bins=df + 1,
            )
            by_power.append({
                "power": pwr,
                "n": int(math.ceil(n)),
            })
        
        # By df
        by_df = []
        for d in [1, 2, 4, 6, 8]:
            n = chi2_power.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=0.80,
                n_bins=d + 1,
            )
            by_df.append({
                "df": d,
                "n": int(math.ceil(n)),
            })
        
        return {
            "by_power_level": by_power,
            "by_df": by_df,
        }


# =============================================================================
# Convenience Functions for MCP
# =============================================================================

def calculate_chisquare_sample_size(
    effect_size: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
    df: Optional[int] = None,
    n_bins: Optional[int] = None,
    n_rows: Optional[int] = None,
    n_cols: Optional[int] = None,
    p_observed: Optional[List[float]] = None,
    p_expected: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate sample size for chi-square test (MCP-friendly wrapper).
    
    Args:
        effect_size: Cohen's w (small=0.1, medium=0.3, large=0.5)
        alpha: Significance level
        power: Desired power
        df: Degrees of freedom
        n_bins: Number of categories (goodness-of-fit)
        n_rows: Rows in contingency table
        n_cols: Columns in contingency table
        p_observed: Observed proportions
        p_expected: Expected proportions
        
    Returns:
        Dictionary with sample size results
    """
    result = ChiSquarePowerAnalysis.calculate_sample_size(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        df=df,
        n_bins=n_bins,
        n_rows=n_rows,
        n_cols=n_cols,
        p_observed=p_observed,
        p_expected=p_expected,
    )
    return result.to_dict()


def calculate_chisquare_power(
    n: int,
    effect_size: Optional[float] = None,
    alpha: float = 0.05,
    df: Optional[int] = None,
    n_bins: Optional[int] = None,
    n_rows: Optional[int] = None,
    n_cols: Optional[int] = None,
    p_observed: Optional[List[float]] = None,
    p_expected: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate power for chi-square test (MCP-friendly wrapper).
    
    Args:
        n: Sample size
        effect_size: Cohen's w
        alpha: Significance level
        df: Degrees of freedom
        n_bins: Number of categories
        n_rows: Rows in contingency table
        n_cols: Columns in contingency table
        p_observed: Observed proportions
        p_expected: Expected proportions
        
    Returns:
        Dictionary with power results
    """
    result = ChiSquarePowerAnalysis.calculate_power(
        n=n,
        effect_size=effect_size,
        alpha=alpha,
        df=df,
        n_bins=n_bins,
        n_rows=n_rows,
        n_cols=n_cols,
        p_observed=p_observed,
        p_expected=p_expected,
    )
    return result.to_dict()

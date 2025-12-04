"""
T-test and Proportion Power Analysis Tools

Tools:
    - calculate_ttest_sample_size
    - calculate_ttest_power
    - calculate_proportion_sample_size
    - calculate_proportion_power
    - ttest_sensitivity_analysis
    - proportion_sensitivity_analysis
    - calculate_effect_size
"""
from typing import List, Optional

from ..base import logger


def register_ttest_power_tools(mcp, stats_client):
    """Register T-test and Proportion power analysis tools."""
    
    @mcp.tool()
    async def calculate_ttest_sample_size(
        effect_size: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        test_type: str = "two-sample",
        alternative: str = "two-sided",
    ) -> dict:
        """
        📊 Calculate required sample size for t-test.
        
        This is the FIRST STEP in clinical research planning.
        Determines how many participants you need to detect a meaningful effect.
        
        Args:
            effect_size: Expected Cohen's d effect size
                - 0.2 = small effect
                - 0.5 = medium effect  
                - 0.8 = large effect
            alpha: Significance level (default: 0.05 for 5% Type I error)
            power: Desired power (default: 0.80 for 80% chance to detect effect)
            ratio: Sample size ratio n2/n1 (default: 1.0 for equal groups)
            test_type: "two-sample" | "paired" | "one-sample"
            alternative: "two-sided" | "larger" | "smaller"
        
        Returns:
            n1: Required sample size for group 1
            n2: Required sample size for group 2 (if applicable)
            total_n: Total sample size needed
            parameters: Input parameters used
            interpretation: Plain-language explanation
            recommendations: Practical advice
        
        Example:
            calculate_ttest_sample_size(effect_size=0.5)
            # Returns: n1=64, n2=64, total=128
        """
        from ..stats_worker_tasks import TTestPowerAnalysis
        
        try:
            analyzer = TTestPowerAnalysis()
            result = analyzer.calculate_sample_size(
                effect_size=effect_size,
                alpha=alpha,
                power=power,
                ratio=ratio,
                test_type=test_type,
                alternative=alternative,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_ttest_sample_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_ttest_power(
        effect_size: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        test_type: str = "two-sample",
        alternative: str = "two-sided",
    ) -> dict:
        """
        ⚡ Calculate statistical power for t-test with given sample size.
        
        Use this to evaluate if your planned study has adequate power
        to detect the expected effect.
        
        Args:
            effect_size: Expected Cohen's d effect size
            n1: Sample size for group 1
            n2: Sample size for group 2 (default: same as n1)
            alpha: Significance level (default: 0.05)
            test_type: "two-sample" | "paired" | "one-sample"
            alternative: "two-sided" | "larger" | "smaller"
        
        Returns:
            power: Achieved statistical power (0-1)
            interpretation: Is this power adequate?
            parameters: Input parameters used
            recommendations: Suggestions if power is low
        """
        from ..stats_worker_tasks import TTestPowerAnalysis
        
        try:
            analyzer = TTestPowerAnalysis()
            result = analyzer.calculate_power(
                effect_size=effect_size,
                n1=n1,
                n2=n2,
                alpha=alpha,
                test_type=test_type,
                alternative=alternative,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_ttest_power error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_proportion_sample_size(
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> dict:
        """
        📊 Calculate required sample size for proportion comparison.
        
        Use this when comparing rates/percentages between two groups.
        
        Args:
            p1: Expected proportion in group 1 (e.g., 0.30 for 30%)
            p2: Expected proportion in group 2 (e.g., 0.45 for 45%)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            ratio: Sample size ratio n2/n1 (default: 1.0)
            alternative: "two-sided" | "larger" | "smaller"
        
        Returns:
            n1: Required sample size for group 1
            n2: Required sample size for group 2
            total_n: Total sample size
            effect_size_h: Cohen's h effect size
        
        Example:
            calculate_proportion_sample_size(p1=0.30, p2=0.45)
            # Returns: n1=152, n2=152, total=304
        """
        from ..stats_worker_tasks import ProportionPowerAnalysis
        
        try:
            analyzer = ProportionPowerAnalysis()
            result = analyzer.calculate_sample_size(
                p1=p1,
                p2=p2,
                alpha=alpha,
                power=power,
                ratio=ratio,
                alternative=alternative,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_proportion_sample_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_proportion_power(
        p1: float,
        p2: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        alternative: str = "two-sided",
    ) -> dict:
        """
        ⚡ Calculate power for proportion comparison with given sample size.
        
        Args:
            p1: Expected proportion in group 1
            p2: Expected proportion in group 2
            n1: Sample size for group 1
            n2: Sample size for group 2 (default: same as n1)
            alpha: Significance level (default: 0.05)
            alternative: "two-sided" | "larger" | "smaller"
        
        Returns:
            power: Achieved statistical power
            effect_size_h: Cohen's h effect size
            interpretation: Adequacy assessment
        """
        from ..stats_worker_tasks import ProportionPowerAnalysis
        
        try:
            analyzer = ProportionPowerAnalysis()
            result = analyzer.calculate_power(
                p1=p1,
                p2=p2,
                n1=n1,
                n2=n2,
                alpha=alpha,
                alternative=alternative,
            )
            return result.to_dict()
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_proportion_power error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def ttest_sensitivity_analysis(
        effect_size: float,
        alpha: float = 0.05,
        power_range: Optional[List[float]] = None,
        ratio: float = 1.0,
        test_type: str = "two-sample",
    ) -> dict:
        """
        📈 Generate power curve and sample size sensitivity analysis.
        
        Shows how sample size requirements change across power levels.
        
        Args:
            effect_size: Expected Cohen's d effect size
            alpha: Significance level (default: 0.05)
            power_range: Power levels to evaluate (default: [0.70-0.95])
            ratio: Sample size ratio n2/n1
            test_type: "two-sample" | "paired" | "one-sample"
        
        Returns:
            sensitivity_table: Sample sizes for each power level
            power_curve_data: Data for plotting power curve
            recommendations: Practical guidance
        """
        from ..stats_worker_tasks import TTestPowerAnalysis
        
        try:
            analyzer = TTestPowerAnalysis()
            result = analyzer.sensitivity_analysis(
                effect_size=effect_size,
                alpha=alpha,
                power_range=power_range,
                ratio=ratio,
                test_type=test_type,
            )
            return result
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"ttest_sensitivity_analysis error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def proportion_sensitivity_analysis(
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power_range: Optional[List[float]] = None,
        ratio: float = 1.0,
    ) -> dict:
        """
        📈 Generate power curve for proportion test.
        
        Args:
            p1: Expected proportion in group 1
            p2: Expected proportion in group 2
            alpha: Significance level
            power_range: Power levels to evaluate
            ratio: Sample size ratio
        
        Returns:
            sensitivity_table: Sample sizes for each power level
            effect_size_h: Cohen's h
        """
        from ..stats_worker_tasks import ProportionPowerAnalysis
        
        try:
            analyzer = ProportionPowerAnalysis()
            result = analyzer.sensitivity_analysis(
                p1=p1,
                p2=p2,
                alpha=alpha,
                power_range=power_range,
                ratio=ratio,
            )
            return result
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"proportion_sensitivity_analysis error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def calculate_effect_size(
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        sd1: Optional[float] = None,
        sd2: Optional[float] = None,
        pooled_sd: Optional[float] = None,
        p1: Optional[float] = None,
        p2: Optional[float] = None,
    ) -> dict:
        """
        🧮 Calculate effect size from study parameters.
        
        For means (Cohen's d):
            Provide mean1, mean2, and either pooled_sd or (sd1, sd2)
            
        For proportions (Cohen's h):
            Provide p1 and p2
        
        Args:
            mean1: Mean of group 1
            mean2: Mean of group 2
            sd1, sd2: Standard deviations
            pooled_sd: Pooled standard deviation
            p1, p2: Proportions
        
        Returns:
            effect_size: Calculated effect size
            effect_type: "Cohen's d" or "Cohen's h"
            interpretation: "small" / "medium" / "large"
        
        Example:
            calculate_effect_size(mean1=100, mean2=115, pooled_sd=30)
            # Returns: Cohen's d = 0.5 (medium effect)
        """
        from ..stats_worker_tasks import (
            cohens_d_from_means,
            cohens_h_from_proportions,
            interpret_effect_size,
        )
        
        try:
            if mean1 is not None and mean2 is not None:
                if pooled_sd is not None:
                    d = cohens_d_from_means(mean1, mean2, pooled_sd=pooled_sd)
                elif sd1 is not None and sd2 is not None:
                    d = cohens_d_from_means(mean1, mean2, sd1=sd1, sd2=sd2)
                else:
                    return {"status": "error", "error": "Need pooled_sd or both sd1 and sd2"}
                
                interpretation = interpret_effect_size(d, "cohens_d")
                return {
                    "effect_size": round(d, 4),
                    "effect_type": "Cohen's d",
                    "interpretation": interpretation,
                    "formula_used": "(mean1 - mean2) / pooled_sd",
                }
            
            elif p1 is not None and p2 is not None:
                h = cohens_h_from_proportions(p1, p2)
                interpretation = interpret_effect_size(h, "cohens_h")
                return {
                    "effect_size": round(h, 4),
                    "effect_type": "Cohen's h",
                    "interpretation": interpretation,
                    "formula_used": "2 * arcsin(√p1) - 2 * arcsin(√p2)",
                }
            
            else:
                return {"status": "error", "error": "Provide means or proportions"}
                
        except ImportError:
            return {"status": "error", "error": "Power analysis module not available"}
        except Exception as e:
            logger.error(f"calculate_effect_size error: {e}")
            return {"status": "error", "error": str(e)}
    
    logger.info("T-test/Proportion power tools registered: 7 tools")

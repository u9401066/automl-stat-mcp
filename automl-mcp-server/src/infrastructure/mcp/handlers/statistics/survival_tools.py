"""
Survival Analysis Tools Module - Time-to-Event Analysis

This module provides MCP tools for survival analysis including
Kaplan-Meier curves, Cox regression, and survival comparisons.

Tools:
    - kaplan_meier_survival: KM curves with log-rank test
    - cox_proportional_hazards: Cox regression
    - compare_survival: Compare survival curves
    - survival_data_summary: Summary statistics for survival data
"""
import base64
from io import StringIO
from typing import List, Optional

import pandas as pd

from .base import logger


def register_survival_tools(mcp, stats_client):
    """Register all survival analysis MCP tools."""
    
    @mcp.tool()
    async def kaplan_meier_survival(
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        time_points: Optional[List[float]] = None,
        alpha: float = 0.05,
        is_base64: bool = False,
    ) -> dict:
        """
        📈 Kaplan-Meier survival analysis with log-rank test.
        
        Performs non-parametric survival analysis:
        - Kaplan-Meier survival curves for each group
        - Median survival time with 95% CI
        - Log-rank test for group comparisons
        - Survival probability at specified time points
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event (e.g., "survival_months")
            event_col: Column name for event indicator (1=event occurred, 0=censored)
            group_col: Optional column for stratification (e.g., "treatment")
            time_points: Specific times to report survival (e.g., [12, 24, 36])
            alpha: Significance level for CI (default: 0.05 for 95% CI)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            survival_curves: KM curves for each group
            median_survival: Median survival with CI per group
            log_rank_test: Test for difference between groups (if grouped)
            survival_at_times: Survival probability at specified times
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import kaplan_meier_analysis, survival_summary
            
            # Get KM analysis
            km_result = kaplan_meier_analysis(
                df, time_col, event_col, group_col, alpha
            )
            
            # Get summary with time points
            summary = survival_summary(
                df, time_col, event_col, group_col, time_points
            )
            
            return {
                "status": "success",
                **km_result,
                "summary": summary,
            }
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            logger.error(f"kaplan_meier_survival error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def cox_proportional_hazards(
        csv_content: str,
        time_col: str,
        event_col: str,
        covariates: Optional[List[str]] = None,
        alpha: float = 0.05,
        is_base64: bool = False,
    ) -> dict:
        """
        🔬 Cox Proportional Hazards regression for survival analysis.
        
        Semi-parametric survival model that estimates hazard ratios:
        - Hazard ratios with 95% CI for each covariate
        - Model fit statistics (log-likelihood, concordance)
        - Wald and likelihood ratio tests
        
        Interpretation:
        - HR > 1: Increased risk of event
        - HR < 1: Decreased risk (protective)
        - HR = 1: No effect
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            covariates: List of covariate columns (default: all numeric)
            alpha: Significance level for CI
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            coefficients: Beta coefficients with SE, HR, CI, p-value
            model_fit: Log-likelihood, concordance index
            global_tests: Wald test, likelihood ratio test
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import cox_regression
            
            result = cox_regression(
                df, time_col, event_col, covariates, alpha
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            logger.error(f"cox_proportional_hazards error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def compare_survival(
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: str,
        is_base64: bool = False,
    ) -> dict:
        """
        ⚖️ Compare survival curves between groups.
        
        Performs comprehensive survival comparison:
        - Kaplan-Meier curves for each group
        - Log-rank test (overall and pairwise)
        - Median survival comparison
        - Hazard ratio estimate
        
        Use this for:
        - Treatment vs control comparison
        - Risk stratification analysis
        - Prognostic factor evaluation
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Column for group stratification
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            groups: Survival statistics per group
            log_rank_test: Test for overall difference
            pairwise_comparisons: Tests between each pair (if >2 groups)
            conclusion: Interpretation of results
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compare_survival_curves
            
            result = compare_survival_curves(
                df, time_col, event_col, group_col
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            logger.error(f"compare_survival error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def survival_data_summary(
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        time_points: Optional[List[float]] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        📋 Get summary statistics for survival data.
        
        Quick overview of survival dataset:
        - Number of subjects, events, censored
        - Follow-up time distribution
        - Median survival per group
        - Event rates
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Optional grouping column
            time_points: Times to report survival (e.g., [12, 24, 36])
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            n_subjects: Total sample size
            n_events: Number of events
            n_censored: Number censored
            follow_up: Follow-up time statistics
            by_group: Statistics per group (if grouped)
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import survival_summary
            
            result = survival_summary(
                df, time_col, event_col, group_col, time_points
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            logger.error(f"survival_data_summary error: {e}")
            return {"status": "error", "error": str(e)}
    
    logger.info("Survival analysis tools registered: 4 tools")

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
from typing import List, Optional

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
            # Submit job to stats-service API
            result = await stats_client.submit_kaplan_meier_job(
                csv_content=csv_content,
                time_col=time_col,
                event_col=event_col,
                group_col=group_col,
                time_points=time_points,
                alpha=alpha,
                is_base64=is_base64,
            )
            return result
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
            # Submit job to stats-service API
            result = await stats_client.submit_cox_regression_job(
                csv_content=csv_content,
                time_col=time_col,
                event_col=event_col,
                covariates=covariates,
                alpha=alpha,
                is_base64=is_base64,
            )
            return result
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
            # Submit job to stats-service API
            result = await stats_client.submit_survival_compare_job(
                csv_content=csv_content,
                time_col=time_col,
                event_col=event_col,
                group_col=group_col,
                is_base64=is_base64,
            )
            return result
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
            # Submit job to stats-service API
            result = await stats_client.submit_survival_summary_job(
                csv_content=csv_content,
                time_column=time_col,
                event_column=event_col,
                group_column=group_col,
                user_id="mcp_user",
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"survival_data_summary error: {e}")
            return {"status": "error", "error": str(e)}

    logger.info("Survival analysis tools registered: 4 tools")

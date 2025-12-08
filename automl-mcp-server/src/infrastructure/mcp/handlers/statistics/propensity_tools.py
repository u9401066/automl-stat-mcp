"""
Propensity Score Analysis Tools Module - Causal Inference

This module provides MCP tools for propensity score analysis,
including score estimation, matching, and treatment effect estimation.

Tools:
    - estimate_propensity_scores: Estimate PS using logistic regression
    - match_propensity_scores: Match treated/control by PS
    - estimate_treatment_effect: Estimate ATE/ATT using IPW
    - assess_covariate_balance: Check balance after adjustment
    - run_propensity_analysis: Complete PS analysis workflow
"""
from typing import List, Optional

from .base import logger


def register_propensity_tools(mcp, stats_client):
    """Register all propensity score analysis MCP tools."""
    
    @mcp.tool()
    async def estimate_propensity_scores(
        csv_content: str,
        treatment_col: str,
        covariates: List[str],
        regularization: float = 0.0,
        is_base64: bool = False,
    ) -> dict:
        """
        📊 Estimate propensity scores using logistic regression.
        
        Propensity score = P(Treatment=1 | Covariates)
        
        Used for:
        - Observational study analysis
        - Controlling for confounding
        - Matching or weighting for causal inference
        
        Model diagnostics include:
        - Pseudo R² (McFadden's)
        - C-statistic (AUC)
        - Brier score
        - Score overlap between groups
        
        Args:
            csv_content: CSV data as string
            treatment_col: Binary treatment column (0/1)
            covariates: List of covariate columns
            regularization: L2 regularization strength (0=none)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            scores: Propensity score for each observation
            coefficients: Model coefficients per covariate
            model_metrics: C-statistic, pseudo R², Brier score
            score_distribution: Stats for treated vs control
            overlap_region: Common support range
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.submit_propensity_estimate_job(
                csv_content=csv_content,
                treatment_col=treatment_col,
                covariates=covariates,
                regularization=regularization,
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"estimate_propensity_scores error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def match_propensity_scores(
        csv_content: str,
        treatment_col: str,
        covariates: Optional[List[str]] = None,
        score_col: Optional[str] = None,
        method: str = "nearest",
        caliper: Optional[float] = 0.2,
        caliper_scale: str = "std",
        replacement: bool = False,
        is_base64: bool = False,
    ) -> dict:
        """
        🔗 Match treated and control units by propensity score.
        
        Creates matched pairs to balance covariate distributions.
        
        Methods:
        - nearest: Greedy nearest neighbor matching
        - optimal: Minimizes total distance (for small datasets)
        
        Args:
            csv_content: CSV data as string
            treatment_col: Binary treatment column
            covariates: Covariates for PS estimation (if score_col not provided)
            score_col: Pre-computed propensity score column
            method: 'nearest' or 'optimal'
            caliper: Max distance for match (in std devs or absolute)
            caliper_scale: 'std' (standard deviations) or 'absolute'
            replacement: Allow control to match multiple treated
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            n_matched_pairs: Number of successful matches
            n_unmatched_treated: Treated units without match
            n_unmatched_control: Control units not used
            matching_rate_treated: Proportion of treated matched
            matched_treated_indices: Row indices of matched treated
            matched_control_indices: Row indices of matched controls
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.submit_propensity_match_job(
                csv_content=csv_content,
                treatment_col=treatment_col,
                covariates=covariates,
                score_col=score_col,
                method=method,
                caliper=caliper,
                caliper_scale=caliper_scale,
                replacement=replacement,
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"match_propensity_scores error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def estimate_treatment_effect(
        csv_content: str,
        outcome_col: str,
        treatment_col: str,
        covariates: Optional[List[str]] = None,
        score_col: Optional[str] = None,
        method: str = "ipw",
        target: str = "ate",
        stabilized: bool = True,
        is_base64: bool = False,
    ) -> dict:
        """
        💊 Estimate causal treatment effect using IPW.
        
        Estimates:
        - ATE: Average Treatment Effect (population)
        - ATT: Average Treatment Effect on Treated
        - ATU: Average Treatment Effect on Untreated
        
        Uses inverse probability weighting to adjust for confounding.
        
        Args:
            csv_content: CSV data as string
            outcome_col: Outcome variable column
            treatment_col: Binary treatment column
            covariates: Covariates for PS estimation
            score_col: Pre-computed propensity score column
            method: 'ipw' or 'iptw'
            target: 'ate', 'att', or 'atu'
            stabilized: Use stabilized weights (recommended)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            effect_type: ATE, ATT, or ATU
            estimate: Point estimate of treatment effect
            std_error: Standard error (bootstrap)
            confidence_interval: 95% CI
            p_value: Two-sided p-value
            significant: Whether effect is significant at α=0.05
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.submit_propensity_effect_job(
                csv_content=csv_content,
                outcome_col=outcome_col,
                treatment_col=treatment_col,
                covariates=covariates,
                score_col=score_col,
                method=method,
                target=target,
                stabilized=stabilized,
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"estimate_treatment_effect error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def assess_covariate_balance(
        csv_content: str,
        treatment_col: str,
        covariates: List[str],
        weights: Optional[List[float]] = None,
        smd_threshold: float = 0.1,
        is_base64: bool = False,
    ) -> dict:
        """
        ⚖️ Assess covariate balance between treatment groups.
        
        Key metrics:
        - SMD (Standardized Mean Difference): <0.1 is ideal
        - Variance Ratio: Should be 0.5-2.0
        - KS Statistic: Distribution difference
        
        Use after matching or weighting to verify balance.
        
        Args:
            csv_content: CSV data as string
            treatment_col: Binary treatment column
            covariates: List of covariate columns
            weights: Optional IPW weights (as list)
            smd_threshold: Threshold for acceptable SMD
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            standardized_mean_differences: SMD per covariate
            variance_ratios: Variance ratio per covariate
            ks_tests: KS statistic and p-value per covariate
            summary: Overall balance summary
            balance_achieved: Whether all covariates balanced
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.submit_propensity_balance_job(
                csv_content=csv_content,
                treatment_col=treatment_col,
                covariates=covariates,
                weights=weights,
                smd_threshold=smd_threshold,
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"assess_covariate_balance error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def run_propensity_analysis(
        csv_content: str,
        outcome_col: str,
        treatment_col: str,
        covariates: List[str],
        method: str = "matching",
        target: str = "ate",
        caliper: Optional[float] = 0.2,
        is_base64: bool = False,
    ) -> dict:
        """
        🎯 Complete propensity score analysis workflow.
        
        All-in-one analysis that performs:
        1. Propensity score estimation
        2. Balance assessment (before)
        3. Matching or IPW weighting
        4. Balance assessment (after)
        5. Treatment effect estimation
        
        Choose method:
        - matching: Create matched pairs (reduces sample size)
        - ipw: Use weights (keeps all data)
        
        Args:
            csv_content: CSV data as string
            outcome_col: Outcome variable column
            treatment_col: Binary treatment column (0/1)
            covariates: List of confounding variables
            method: 'matching' or 'ipw'
            target: 'ate' (population), 'att' (treated), 'atu' (untreated)
            caliper: For matching, max distance in std devs
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            propensity_model: PS estimation results
            balance_before: Covariate balance pre-adjustment
            balance_after: Covariate balance post-adjustment
            method_details: Matching/weighting specifics
            treatment_effect: Effect estimate with CI and p-value
        """
        try:
            # Submit job to stats-service API
            result = await stats_client.submit_propensity_full_job(
                csv_content=csv_content,
                outcome_col=outcome_col,
                treatment_col=treatment_col,
                covariates=covariates,
                method=method,
                target=target,
                caliper=caliper,
                is_base64=is_base64,
            )
            return result
        except Exception as e:
            logger.error(f"run_propensity_analysis error: {e}")
            return {"status": "error", "error": str(e)}
    
    logger.info("Propensity score tools registered: 5 tools")

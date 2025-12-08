"""
HTTP Client for Stats Service

Handles communication with the Stats Service REST API.
"""
import os
import httpx
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# Stats service URL from environment
STATS_SERVICE_URL = os.getenv("STATS_SERVICE_URL", "http://localhost:8003")


@dataclass
class StatsClient:
    """Client for Stats Service REST API"""
    
    base_url: str = STATS_SERVICE_URL
    timeout: int = 30

    async def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Stats Service"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()

    # ============== EDA Operations ==============
    
    async def submit_eda_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        title: Optional[str] = "EDA Report",
        minimal: bool = True,
    ) -> Dict[str, Any]:
        """Submit an EDA job"""
        return await self._request(
            "POST",
            "/eda/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "title": title,
                "minimal": minimal,
            },
        )
    
    async def preview_dataset(
        self,
        dataset_id: str,
        n_rows: int = 10,
    ) -> Dict[str, Any]:
        """Preview dataset"""
        return await self._request(
            "POST",
            "/eda/preview",
            params={"dataset_id": dataset_id, "n_rows": n_rows},
        )

    # ============== TableOne Operations ==============
    
    async def submit_tableone_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        columns: Optional[List[str]] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        groupby: Optional[str] = None,
        nonnormal: Optional[List[str]] = None,
        pval: bool = False,
    ) -> Dict[str, Any]:
        """Submit a TableOne job"""
        return await self._request(
            "POST",
            "/tableone/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "columns": columns,
                "categorical": categorical,
                "continuous": continuous,
                "groupby": groupby,
                "nonnormal": nonnormal,
                "pval": pval,
            },
        )
    
    async def get_column_suggestions(
        self,
        dataset_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get column type suggestions for TableOne"""
        return await self._request(
            "POST",
            "/tableone/columns",
            params={"dataset_id": dataset_id, "user_id": user_id},
        )

    # ============== Auto-Analyze Operations ==============
    
    async def submit_auto_analyze_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an auto-analyze job"""
        return await self._request(
            "POST",
            "/auto-analyze/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "target_column": target_column,
            },
        )
    
    async def get_auto_analyze_capabilities(self) -> Dict[str, Any]:
        """Get auto-analyze capabilities"""
        return await self._request(
            "GET",
            "/auto-analyze/capabilities",
        )

    # ============== Job Operations ==============
    
    async def get_job_status(
        self,
        job_id: str,
    ) -> Dict[str, Any]:
        """Get job status"""
        return await self._request(
            "GET",
            f"/jobs/{job_id}",
        )
    
    async def get_job_result(
        self,
        job_id: str,
    ) -> Dict[str, Any]:
        """Get job result"""
        return await self._request(
            "GET",
            f"/jobs/{job_id}/result",
        )
    
    async def list_jobs(
        self,
        user_id: str,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List jobs for a user"""
        params = {"user_id": user_id, "limit": limit}
        if job_type:
            params["job_type"] = job_type
        
        return await self._request(
            "GET",
            "/jobs/",
            params=params,
        )
    
    async def delete_job(
        self,
        job_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Delete a job"""
        return await self._request(
            "DELETE",
            f"/jobs/{job_id}",
            params={"user_id": user_id},
        )
    
    # ============== Direct Analysis ==============
    
    async def direct_analyze(
        self,
        csv_content: str,
        user_id: str,
        target_column: Optional[str] = None,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        """Submit direct analysis (no MinIO storage)"""
        return await self._request(
            "POST",
            "/direct/analyze",
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
                "user_id": user_id,
                "target_column": target_column,
            },
        )
    
    async def quick_stats(
        self,
        csv_content: str,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        """Get quick stats synchronously"""
        return await self._request(
            "POST",
            "/direct/quick-stats",
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
            },
        )

    # ============== Propensity Score Analysis ==============
    
    async def submit_propensity_estimate_job(
        self,
        dataset_id: str,
        user_id: str,
        treatment_column: str,
        covariates: List[str],
        method: str = "logistic",
        regularization: float = 0.0,
    ) -> Dict[str, Any]:
        """Submit propensity score estimation job"""
        return await self._request(
            "POST",
            "/propensity/estimate/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "treatment_column": treatment_column,
                "covariates": covariates,
                "method": method,
                "regularization": regularization,
            },
        )
    
    async def submit_propensity_match_job(
        self,
        dataset_id: str,
        user_id: str,
        treatment_column: str,
        covariates: Optional[List[str]] = None,
        score_column: Optional[str] = None,
        method: str = "nearest",
        caliper: float = 0.2,
        caliper_scale: str = "std",
        replacement: bool = False,
        ratio: int = 1,
    ) -> Dict[str, Any]:
        """Submit propensity score matching job"""
        return await self._request(
            "POST",
            "/propensity/match/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "treatment_column": treatment_column,
                "covariates": covariates,
                "score_column": score_column,
                "method": method,
                "caliper": caliper,
                "caliper_scale": caliper_scale,
                "replacement": replacement,
                "ratio": ratio,
            },
        )
    
    async def submit_treatment_effect_job(
        self,
        dataset_id: str,
        user_id: str,
        treatment_column: str,
        outcome_column: str,
        covariates: Optional[List[str]] = None,
        score_column: Optional[str] = None,
        method: str = "ipw",
        estimand: str = "ATE",
    ) -> Dict[str, Any]:
        """Submit treatment effect estimation job"""
        return await self._request(
            "POST",
            "/propensity/effect/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "treatment_column": treatment_column,
                "outcome_column": outcome_column,
                "covariates": covariates,
                "score_column": score_column,
                "method": method,
                "estimand": estimand,
            },
        )
    
    async def submit_balance_check_job(
        self,
        dataset_id: str,
        user_id: str,
        treatment_column: str,
        covariates: List[str],
        weights_column: Optional[str] = None,
        matched_column: Optional[str] = None,
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """Submit covariate balance assessment job"""
        return await self._request(
            "POST",
            "/propensity/balance/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "treatment_column": treatment_column,
                "covariates": covariates,
                "weights_column": weights_column,
                "matched_column": matched_column,
                "threshold": threshold,
            },
        )
    
    async def submit_full_propensity_job(
        self,
        dataset_id: str,
        user_id: str,
        treatment_column: str,
        outcome_column: str,
        covariates: List[str],
        method: str = "matching",
        caliper: float = 0.2,
    ) -> Dict[str, Any]:
        """Submit full propensity score analysis job"""
        return await self._request(
            "POST",
            "/propensity/full/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "treatment_column": treatment_column,
                "outcome_column": outcome_column,
                "covariates": covariates,
                "method": method,
                "caliper": caliper,
            },
        )
    
    async def get_propensity_methods(self) -> Dict[str, Any]:
        """Get available propensity score methods"""
        return await self._request("GET", "/propensity/methods")

    # ============== Survival Analysis ==============
    
    async def submit_kaplan_meier_job(
        self,
        dataset_id: str,
        user_id: str,
        time_column: str,
        event_column: str,
        group_column: Optional[str] = None,
        confidence_level: float = 0.95,
        time_points: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Submit Kaplan-Meier analysis job"""
        return await self._request(
            "POST",
            "/survival/kaplan-meier/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "time_column": time_column,
                "event_column": event_column,
                "group_column": group_column,
                "confidence_level": confidence_level,
                "time_points": time_points,
            },
        )
    
    async def submit_cox_regression_job(
        self,
        dataset_id: str,
        user_id: str,
        time_column: str,
        event_column: str,
        covariates: List[str],
        strata: Optional[List[str]] = None,
        ties: str = "efron",
        penalizer: float = 0.0,
    ) -> Dict[str, Any]:
        """Submit Cox proportional hazards regression job"""
        return await self._request(
            "POST",
            "/survival/cox/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "time_column": time_column,
                "event_column": event_column,
                "covariates": covariates,
                "strata": strata,
                "ties": ties,
                "penalizer": penalizer,
            },
        )
    
    async def submit_survival_compare_job(
        self,
        dataset_id: str,
        user_id: str,
        time_column: str,
        event_column: str,
        group_column: str,
        test: str = "logrank",
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """Submit survival curve comparison job"""
        return await self._request(
            "POST",
            "/survival/compare/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "time_column": time_column,
                "event_column": event_column,
                "group_column": group_column,
                "test": test,
                "confidence_level": confidence_level,
            },
        )
    
    async def submit_survival_summary_job(
        self,
        dataset_id: str,
        user_id: str,
        time_column: str,
        event_column: str,
        group_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit survival data summary job"""
        return await self._request(
            "POST",
            "/survival/summary/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "time_column": time_column,
                "event_column": event_column,
                "group_column": group_column,
            },
        )
    
    async def get_survival_methods(self) -> Dict[str, Any]:
        """Get available survival analysis methods"""
        return await self._request("GET", "/survival/methods")

    # ============== ROC/AUC Analysis ==============
    
    async def submit_roc_compute_job(
        self,
        dataset_id: str,
        user_id: str,
        true_column: str,
        score_column: str,
        pos_label: int = 1,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """Submit ROC curve computation job"""
        return await self._request(
            "POST",
            "/roc/compute/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "true_column": true_column,
                "score_column": score_column,
                "pos_label": pos_label,
                "n_bootstrap": n_bootstrap,
                "confidence_level": confidence_level,
            },
        )
    
    async def submit_roc_compare_job(
        self,
        dataset_id: str,
        user_id: str,
        true_column: str,
        score_columns: List[str],
        model_names: Optional[List[str]] = None,
        method: str = "delong",
    ) -> Dict[str, Any]:
        """Submit ROC curves comparison job"""
        return await self._request(
            "POST",
            "/roc/compare/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "true_column": true_column,
                "score_columns": score_columns,
                "model_names": model_names,
                "method": method,
            },
        )
    
    async def submit_threshold_analysis_job(
        self,
        dataset_id: str,
        user_id: str,
        true_column: str,
        score_column: str,
        method: str = "youden",
        cost_fp: float = 1.0,
        cost_fn: float = 1.0,
        min_sensitivity: Optional[float] = None,
        min_specificity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Submit optimal threshold analysis job"""
        return await self._request(
            "POST",
            "/roc/threshold/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "true_column": true_column,
                "score_column": score_column,
                "method": method,
                "cost_fp": cost_fp,
                "cost_fn": cost_fn,
                "min_sensitivity": min_sensitivity,
                "min_specificity": min_specificity,
            },
        )
    
    async def submit_calibration_job(
        self,
        dataset_id: str,
        user_id: str,
        true_column: str,
        score_column: str,
        n_bins: int = 10,
        strategy: str = "uniform",
    ) -> Dict[str, Any]:
        """Submit calibration analysis job"""
        return await self._request(
            "POST",
            "/roc/calibration/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "true_column": true_column,
                "score_column": score_column,
                "n_bins": n_bins,
                "strategy": strategy,
            },
        )
    
    async def submit_full_evaluation_job(
        self,
        dataset_id: str,
        user_id: str,
        true_column: str,
        score_column: str,
        threshold: Optional[float] = None,
        include_calibration: bool = True,
        include_precision_recall: bool = True,
    ) -> Dict[str, Any]:
        """Submit full classifier evaluation job"""
        return await self._request(
            "POST",
            "/roc/full-eval/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "true_column": true_column,
                "score_column": score_column,
                "threshold": threshold,
                "include_calibration": include_calibration,
                "include_precision_recall": include_precision_recall,
            },
        )
    
    async def get_roc_methods(self) -> Dict[str, Any]:
        """Get available ROC analysis methods"""
        return await self._request("GET", "/roc/methods")

    # ============== Power Analysis ==============
    
    async def calculate_ttest_power(
        self,
        effect_size: Optional[float] = None,
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        std: Optional[float] = None,
        alpha: float = 0.05,
        power: Optional[float] = 0.8,
        n: Optional[int] = None,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Calculate t-test power or sample size"""
        return await self._request(
            "POST",
            "/power/ttest",
            json={
                "effect_size": effect_size,
                "mean1": mean1,
                "mean2": mean2,
                "std": std,
                "alpha": alpha,
                "power": power,
                "n": n,
                "ratio": ratio,
                "alternative": alternative,
            },
        )
    
    async def calculate_proportion_power(
        self,
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power: Optional[float] = 0.8,
        n: Optional[int] = None,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Calculate proportion test power or sample size"""
        return await self._request(
            "POST",
            "/power/proportion",
            json={
                "p1": p1,
                "p2": p2,
                "alpha": alpha,
                "power": power,
                "n": n,
                "ratio": ratio,
                "alternative": alternative,
            },
        )
    
    async def calculate_anova_power(
        self,
        k: int,
        effect_size: Optional[float] = None,
        means: Optional[List[float]] = None,
        std: Optional[float] = None,
        alpha: float = 0.05,
        power: Optional[float] = 0.8,
        n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate ANOVA power or sample size"""
        return await self._request(
            "POST",
            "/power/anova",
            json={
                "k": k,
                "effect_size": effect_size,
                "means": means,
                "std": std,
                "alpha": alpha,
                "power": power,
                "n": n,
            },
        )
    
    async def calculate_chisquare_power(
        self,
        effect_size: Optional[float] = None,
        contingency_table: Optional[List[List[float]]] = None,
        df: Optional[int] = None,
        alpha: float = 0.05,
        power: Optional[float] = 0.8,
        n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate chi-square power or sample size"""
        return await self._request(
            "POST",
            "/power/chi-square",
            json={
                "effect_size": effect_size,
                "contingency_table": contingency_table,
                "df": df,
                "alpha": alpha,
                "power": power,
                "n": n,
            },
        )
    
    async def calculate_survival_power(
        self,
        hazard_ratio: float,
        p1: float,
        alpha: float = 0.05,
        power: Optional[float] = 0.8,
        n_events: Optional[int] = None,
        ratio: float = 1.0,
        dropout_rate: float = 0.0,
        accrual_time: Optional[float] = None,
        followup_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculate survival analysis power or sample size"""
        return await self._request(
            "POST",
            "/power/survival",
            json={
                "hazard_ratio": hazard_ratio,
                "p1": p1,
                "alpha": alpha,
                "power": power,
                "n_events": n_events,
                "ratio": ratio,
                "dropout_rate": dropout_rate,
                "accrual_time": accrual_time,
                "followup_time": followup_time,
            },
        )
    
    async def calculate_effect_size(
        self,
        test_type: str,
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        std: Optional[float] = None,
        p1: Optional[float] = None,
        p2: Optional[float] = None,
        means: Optional[List[float]] = None,
        contingency_table: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Calculate effect size from raw data"""
        return await self._request(
            "POST",
            "/power/effect-size",
            json={
                "test_type": test_type,
                "mean1": mean1,
                "mean2": mean2,
                "std": std,
                "p1": p1,
                "p2": p2,
                "means": means,
                "contingency_table": contingency_table,
            },
        )
    
    async def get_power_guidelines(self) -> Dict[str, Any]:
        """Get power analysis guidelines"""
        return await self._request("GET", "/power/guidelines")

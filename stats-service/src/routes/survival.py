"""
Stats Service - Survival Analysis Routes

Routes for time-to-event analysis:
- Kaplan-Meier estimation
- Cox proportional hazards regression
- Log-rank test for group comparison
- Survival curves comparison
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from ..infrastructure.redis_dataset_store import redis_dataset_store
from ..infrastructure.repositories import get_job_repository, get_job_queue

router = APIRouter(prefix="/survival", tags=["Survival Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class KaplanMeierRequest(BaseModel):
    """Request for Kaplan-Meier analysis"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    time_column: str = Field(..., description="Time-to-event column")
    event_column: str = Field(..., description="Event indicator (1=event, 0=censored)")
    group_column: Optional[str] = Field(None, description="Optional grouping variable")
    confidence_level: float = Field(default=0.95, description="Confidence level for CI")
    time_points: Optional[List[float]] = Field(None, description="Specific time points for survival estimates")


class CoxRegressionRequest(BaseModel):
    """Request for Cox proportional hazards regression"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    time_column: str = Field(..., description="Time-to-event column")
    event_column: str = Field(..., description="Event indicator")
    covariates: List[str] = Field(..., description="Covariates to include")
    strata: Optional[List[str]] = Field(None, description="Stratification variables")
    ties: str = Field(default="efron", description="Tie handling: efron, breslow, exact")
    penalizer: float = Field(default=0.0, description="L2 regularization")


class SurvivalCompareRequest(BaseModel):
    """Request for survival curve comparison"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    time_column: str = Field(..., description="Time-to-event column")
    event_column: str = Field(..., description="Event indicator")
    group_column: str = Field(..., description="Grouping variable for comparison")
    test: str = Field(default="logrank", description="Test: logrank, wilcoxon, tarone-ware")
    confidence_level: float = Field(default=0.95, description="Confidence level")


class SurvivalSummaryRequest(BaseModel):
    """Request for survival data summary"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    time_column: str = Field(..., description="Time-to-event column")
    event_column: str = Field(..., description="Event indicator")
    group_column: Optional[str] = Field(None, description="Optional grouping variable")


class JobResponse(BaseModel):
    """Standard job submission response"""
    job_id: str
    job_type: str
    status: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

async def _submit_survival_job(
    job_type: str,
    dataset_id: str,
    user_id: str,
    config: dict,
) -> JobResponse:
    """Submit a survival analysis job to the queue"""
    import uuid
    
    job_repo = get_job_repository()
    job_queue = get_job_queue()
    
    # Verify dataset exists
    dataset = await redis_dataset_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    # Create job
    job_id = f"survival-{uuid.uuid4().hex[:12]}"
    
    job_data = {
        "job_id": job_id,
        "job_type": job_type,
        "user_id": user_id,
        "dataset_id": dataset_id,
        "config": config,
        "status": "pending",
    }
    
    # Save to repository
    await job_repo.create(job_data)
    
    # Queue for processing
    await job_queue.enqueue(job_data)
    
    return JobResponse(
        job_id=job_id,
        job_type=job_type,
        status="pending",
        message=f"Survival {job_type} job submitted successfully",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/kaplan-meier/submit", response_model=JobResponse)
async def submit_kaplan_meier_job(request: KaplanMeierRequest):
    """
    📈 Submit Kaplan-Meier survival analysis job.
    
    Non-parametric estimation of survival function S(t).
    
    Output includes:
    - Survival function estimates at each time point
    - Confidence intervals (Greenwood's formula)
    - Median survival time
    - Restricted mean survival time (RMST)
    - Survival plot data
    
    Args:
        time_column: Follow-up time
        event_column: 1 if event occurred, 0 if censored
        group_column: Optional grouping for stratified analysis
        confidence_level: CI level (default 0.95)
        time_points: Specific times for survival estimates
    """
    config = {
        "time_column": request.time_column,
        "event_column": request.event_column,
        "group_column": request.group_column,
        "confidence_level": request.confidence_level,
        "time_points": request.time_points,
    }
    
    return await _submit_survival_job(
        job_type="kaplan_meier",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/cox/submit", response_model=JobResponse)
async def submit_cox_regression_job(request: CoxRegressionRequest):
    """
    📊 Submit Cox proportional hazards regression job.
    
    Semi-parametric model: h(t|X) = h₀(t) × exp(β'X)
    
    Output includes:
    - Hazard ratios with confidence intervals
    - P-values for each covariate
    - Concordance index (C-statistic)
    - Log-likelihood and AIC/BIC
    - Schoenfeld residuals for PH assumption check
    - Martingale residuals for functional form
    
    Args:
        time_column: Follow-up time
        event_column: Event indicator
        covariates: Variables to include in model
        strata: Variables for stratification (separate baseline hazards)
        ties: Method for tied event times
        penalizer: L2 regularization strength
    """
    config = {
        "time_column": request.time_column,
        "event_column": request.event_column,
        "covariates": request.covariates,
        "strata": request.strata,
        "ties": request.ties,
        "penalizer": request.penalizer,
    }
    
    return await _submit_survival_job(
        job_type="cox_regression",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/compare/submit", response_model=JobResponse)
async def submit_survival_comparison_job(request: SurvivalCompareRequest):
    """
    🔬 Submit survival curve comparison job.
    
    Compares survival distributions between groups.
    
    Tests available:
    - Log-rank: Equal weights across time
    - Wilcoxon: Weights early differences more
    - Tarone-Ware: Compromise between log-rank and Wilcoxon
    
    Output includes:
    - Test statistic and p-value
    - Hazard ratio estimate
    - Median survival by group
    - Survival at specific time points
    - KM plot data for visualization
    """
    config = {
        "time_column": request.time_column,
        "event_column": request.event_column,
        "group_column": request.group_column,
        "test": request.test,
        "confidence_level": request.confidence_level,
    }
    
    return await _submit_survival_job(
        job_type="survival_compare",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/summary/submit", response_model=JobResponse)
async def submit_survival_summary_job(request: SurvivalSummaryRequest):
    """
    📋 Submit survival data summary job.
    
    Quick overview of survival dataset:
    - Total subjects, events, censoring rate
    - Follow-up time distribution
    - Event rate over time
    - Summary by group (if provided)
    
    Useful before running detailed analyses.
    """
    config = {
        "time_column": request.time_column,
        "event_column": request.event_column,
        "group_column": request.group_column,
    }
    
    return await _submit_survival_job(
        job_type="survival_summary",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.get("/methods")
async def get_survival_methods():
    """
    📋 Get available survival analysis methods and their descriptions.
    """
    return {
        "analyses": {
            "kaplan_meier": {
                "name": "Kaplan-Meier Estimator",
                "description": "Non-parametric survival function estimation",
                "assumptions": [
                    "Censoring is non-informative",
                    "Survival probability is the same regardless of entry time",
                ],
                "output": ["Survival curve", "Median survival", "Confidence intervals"],
            },
            "cox_regression": {
                "name": "Cox Proportional Hazards",
                "description": "Semi-parametric regression for survival",
                "assumptions": [
                    "Proportional hazards (constant HR over time)",
                    "Log-linear relationship between hazard and covariates",
                ],
                "output": ["Hazard ratios", "P-values", "C-index", "Residuals"],
            },
            "logrank_test": {
                "name": "Log-Rank Test",
                "description": "Compare survival between groups",
                "assumptions": [
                    "Proportional hazards between groups",
                    "Non-informative censoring",
                ],
                "output": ["Chi-square statistic", "P-value", "Hazard ratio"],
            },
        },
        "tie_methods": {
            "efron": "Efron approximation (recommended, default)",
            "breslow": "Breslow approximation (faster, less accurate with many ties)",
            "exact": "Exact partial likelihood (slow, most accurate)",
        },
        "comparison_tests": {
            "logrank": "Log-rank test - equal weights, sensitive to late differences",
            "wilcoxon": "Wilcoxon (Gehan) - weights early events more heavily",
            "tarone-ware": "Tarone-Ware - compromise between log-rank and Wilcoxon",
        },
    }

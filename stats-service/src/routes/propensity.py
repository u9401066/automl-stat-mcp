"""
Stats Service - Propensity Score Analysis Routes

Routes for causal inference using propensity score methods:
- Propensity score estimation
- Propensity score matching
- Treatment effect estimation
- Balance diagnostics
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from ..infrastructure.redis_dataset_store import redis_dataset_store
from ..infrastructure.repositories import get_job_repository, get_job_queue

router = APIRouter(prefix="/propensity", tags=["Propensity Score Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PropensityEstimateRequest(BaseModel):
    """Request for propensity score estimation"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column (0/1)")
    covariates: List[str] = Field(..., description="List of covariate columns")
    method: str = Field(default="logistic", description="Estimation method: logistic, gbm, random_forest")
    regularization: float = Field(default=0.0, description="L2 regularization strength")


class PropensityMatchRequest(BaseModel):
    """Request for propensity score matching"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    covariates: Optional[List[str]] = Field(None, description="Covariates for PS estimation (if score_column not provided)")
    score_column: Optional[str] = Field(None, description="Pre-computed propensity score column")
    method: str = Field(default="nearest", description="Matching method: nearest, optimal, caliper")
    caliper: float = Field(default=0.2, description="Maximum distance for match")
    caliper_scale: str = Field(default="std", description="Caliper scale: std or absolute")
    replacement: bool = Field(default=False, description="Allow matching with replacement")
    ratio: int = Field(default=1, description="Control:Treated ratio (1 = 1:1 matching)")


class TreatmentEffectRequest(BaseModel):
    """Request for treatment effect estimation"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    outcome_column: str = Field(..., description="Outcome variable column")
    covariates: Optional[List[str]] = Field(None, description="Covariates for adjustment")
    score_column: Optional[str] = Field(None, description="Pre-computed propensity score column")
    method: str = Field(default="ipw", description="Method: ipw (Inverse Probability Weighting), matching, doubly_robust")
    estimand: str = Field(default="ATE", description="Estimand: ATE, ATT, or ATU")


class BalanceCheckRequest(BaseModel):
    """Request for covariate balance assessment"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    covariates: List[str] = Field(..., description="Covariates to check balance")
    weights_column: Optional[str] = Field(None, description="Weights column (for IPW)")
    matched_column: Optional[str] = Field(None, description="Matched indicator column")
    threshold: float = Field(default=0.1, description="SMD threshold for imbalance")


class PropensityFullRequest(BaseModel):
    """Request for full propensity score analysis workflow"""
    dataset_id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    outcome_column: str = Field(..., description="Outcome variable column")
    covariates: List[str] = Field(..., description="Covariates for analysis")
    method: str = Field(default="matching", description="Method: matching or ipw")
    caliper: float = Field(default=0.2, description="Caliper for matching")


class JobResponse(BaseModel):
    """Standard job submission response"""
    job_id: str
    job_type: str
    status: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

async def _submit_propensity_job(
    job_type: str,
    dataset_id: str,
    user_id: str,
    config: dict,
) -> JobResponse:
    """Submit a propensity score analysis job to the queue"""
    import uuid
    
    job_repo = get_job_repository()
    job_queue = get_job_queue()
    
    # Verify dataset exists
    dataset = await redis_dataset_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    # Create job
    job_id = f"propensity-{uuid.uuid4().hex[:12]}"
    
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
        message=f"Propensity {job_type} job submitted successfully",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/estimate/submit", response_model=JobResponse)
async def submit_propensity_estimate_job(request: PropensityEstimateRequest):
    """
    📊 Submit propensity score estimation job.
    
    Estimates P(Treatment=1 | Covariates) using specified method.
    
    Model diagnostics include:
    - Pseudo R² (McFadden's)
    - C-statistic (AUC)
    - Brier score
    - Score overlap between groups
    
    Args:
        dataset_id: Dataset to analyze
        treatment_column: Binary treatment (0/1)
        covariates: Variables to include in model
        method: logistic, gbm, or random_forest
        regularization: L2 penalty (for logistic)
    
    Returns:
        job_id for tracking
    """
    config = {
        "treatment_column": request.treatment_column,
        "covariates": request.covariates,
        "method": request.method,
        "regularization": request.regularization,
    }
    
    return await _submit_propensity_job(
        job_type="propensity_estimate",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/match/submit", response_model=JobResponse)
async def submit_propensity_match_job(request: PropensityMatchRequest):
    """
    🔗 Submit propensity score matching job.
    
    Creates matched pairs to balance covariate distributions.
    
    Methods:
    - nearest: Greedy nearest neighbor matching
    - optimal: Minimizes total distance (for small datasets)
    - caliper: Nearest within caliper distance
    
    Args:
        dataset_id: Dataset to analyze
        treatment_column: Binary treatment
        covariates: For PS estimation (or provide score_column)
        score_column: Pre-computed PS column
        method: nearest, optimal, or caliper
        caliper: Max distance for match
        ratio: Control:Treated ratio
    
    Returns:
        job_id for tracking
    """
    config = {
        "treatment_column": request.treatment_column,
        "covariates": request.covariates,
        "score_column": request.score_column,
        "method": request.method,
        "caliper": request.caliper,
        "caliper_scale": request.caliper_scale,
        "replacement": request.replacement,
        "ratio": request.ratio,
    }
    
    return await _submit_propensity_job(
        job_type="propensity_match",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/effect/submit", response_model=JobResponse)
async def submit_treatment_effect_job(request: TreatmentEffectRequest):
    """
    📈 Submit treatment effect estimation job.
    
    Estimates causal effect of treatment on outcome.
    
    Estimands:
    - ATE: Average Treatment Effect (population)
    - ATT: Average Treatment Effect on Treated
    - ATU: Average Treatment Effect on Untreated
    
    Methods:
    - ipw: Inverse Probability Weighting
    - matching: PS matching then outcome comparison
    - doubly_robust: IPW + outcome regression
    
    Returns:
        Point estimate, confidence interval, p-value
    """
    config = {
        "treatment_column": request.treatment_column,
        "outcome_column": request.outcome_column,
        "covariates": request.covariates,
        "score_column": request.score_column,
        "method": request.method,
        "estimand": request.estimand,
    }
    
    return await _submit_propensity_job(
        job_type="propensity_effect",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/balance/submit", response_model=JobResponse)
async def submit_balance_check_job(request: BalanceCheckRequest):
    """
    ⚖️ Submit covariate balance assessment job.
    
    Checks if covariates are balanced between treatment groups
    after matching or weighting.
    
    Metrics:
    - Standardized Mean Difference (SMD)
    - Variance Ratio
    - KS statistic (for distributions)
    - Rubin's rules compliance
    
    Returns:
        Balance table with before/after comparison
    """
    config = {
        "treatment_column": request.treatment_column,
        "covariates": request.covariates,
        "weights_column": request.weights_column,
        "matched_column": request.matched_column,
        "threshold": request.threshold,
    }
    
    return await _submit_propensity_job(
        job_type="propensity_balance",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.post("/full/submit", response_model=JobResponse)
async def submit_full_propensity_analysis(request: PropensityFullRequest):
    """
    🚀 Submit complete propensity score analysis workflow.
    
    Performs end-to-end causal inference:
    1. Estimate propensity scores
    2. Match or weight observations
    3. Check covariate balance
    4. Estimate treatment effect
    5. Sensitivity analysis
    
    Returns comprehensive report with all diagnostics.
    """
    config = {
        "treatment_column": request.treatment_column,
        "outcome_column": request.outcome_column,
        "covariates": request.covariates,
        "method": request.method,
        "caliper": request.caliper,
    }
    
    return await _submit_propensity_job(
        job_type="propensity_full",
        dataset_id=request.dataset_id,
        user_id=request.user_id,
        config=config,
    )


@router.get("/methods")
async def get_propensity_methods():
    """
    📋 Get available propensity score methods and their descriptions.
    """
    return {
        "estimation_methods": {
            "logistic": {
                "name": "Logistic Regression",
                "description": "Standard method, interpretable coefficients",
                "pros": ["Interpretable", "Fast", "Well-studied"],
                "cons": ["Assumes linear logit", "May not capture interactions"],
            },
            "gbm": {
                "name": "Gradient Boosting Machine",
                "description": "Non-parametric, captures complex relationships",
                "pros": ["Flexible", "Handles interactions", "Often better balance"],
                "cons": ["Black-box", "May overfit"],
            },
            "random_forest": {
                "name": "Random Forest",
                "description": "Ensemble method, robust to outliers",
                "pros": ["Robust", "No assumptions", "Handles missing data"],
                "cons": ["Black-box", "Computationally intensive"],
            },
        },
        "matching_methods": {
            "nearest": {
                "name": "Nearest Neighbor",
                "description": "Greedy matching to closest control",
                "pros": ["Fast", "Simple"],
                "cons": ["Order-dependent", "May not be optimal"],
            },
            "optimal": {
                "name": "Optimal Matching",
                "description": "Minimizes total distance across all pairs",
                "pros": ["Globally optimal"],
                "cons": ["Slow for large datasets"],
            },
            "caliper": {
                "name": "Caliper Matching",
                "description": "Nearest neighbor within maximum distance",
                "pros": ["Prevents bad matches"],
                "cons": ["May leave units unmatched"],
            },
        },
        "estimands": {
            "ATE": "Average Treatment Effect - effect on random person from population",
            "ATT": "Average Treatment Effect on Treated - effect on those who received treatment",
            "ATU": "Average Treatment Effect on Untreated - effect on those who didn't receive treatment",
        },
    }

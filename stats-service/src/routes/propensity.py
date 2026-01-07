"""
Stats Service - Propensity Score Analysis Routes

Routes for causal inference using propensity score methods:
- Propensity score estimation
- Propensity score matching
- Treatment effect estimation
- Balance diagnostics

Supports two modes:
1. Dataset mode: Provide dataset_id (pre-uploaded to MinIO)
2. Direct mode: Provide csv_content inline (no storage)
"""
import base64
import json
import uuid
from datetime import datetime
from typing import List, Optional

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..config import REDIS_DB, REDIS_HOST, REDIS_PORT, STATS_JOBS_PENDING, STATS_JOBS_PREFIX
from ..infrastructure.redis_dataset_store import redis_dataset_store

router = APIRouter(prefix="/propensity", tags=["Propensity Score Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PropensityEstimateRequest(BaseModel):
    """Request for propensity score estimation

    Provide EITHER dataset_id OR csv_content, not both.
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (if using pre-uploaded data)")
    csv_content: Optional[str] = Field(None, description="CSV data as string (if using direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column (0/1)")
    covariates: List[str] = Field(..., description="List of covariate columns")
    method: str = Field(default="logistic", description="Estimation method: logistic, gbm, random_forest")
    regularization: float = Field(default=0.0, description="L2 regularization strength")

    @field_validator('dataset_id', 'csv_content')
    @classmethod
    def check_data_source(cls, v, info):
        return v  # Validation done in model_validator


class PropensityMatchRequest(BaseModel):
    """Request for propensity score matching"""
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    csv_content: Optional[str] = Field(None, description="CSV data as string")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
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
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    csv_content: Optional[str] = Field(None, description="CSV data as string")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    outcome_column: str = Field(..., description="Outcome variable column")
    covariates: Optional[List[str]] = Field(None, description="Covariates for adjustment")
    score_column: Optional[str] = Field(None, description="Pre-computed propensity score column")
    method: str = Field(default="ipw", description="Method: ipw (Inverse Probability Weighting), matching, doubly_robust")
    estimand: str = Field(default="ATE", description="Estimand: ATE, ATT, or ATU")


class BalanceCheckRequest(BaseModel):
    """Request for covariate balance assessment"""
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    csv_content: Optional[str] = Field(None, description="CSV data as string")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    treatment_column: str = Field(..., description="Binary treatment column")
    covariates: List[str] = Field(..., description="Covariates to check balance")
    weights_column: Optional[str] = Field(None, description="Weights column (for IPW)")
    matched_column: Optional[str] = Field(None, description="Matched indicator column")
    threshold: float = Field(default=0.1, description="SMD threshold for imbalance")


class PropensityFullRequest(BaseModel):
    """Request for full propensity score analysis workflow"""
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    csv_content: Optional[str] = Field(None, description="CSV data as string")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
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

# Redis connection pool for async operations
_redis_pool = None

async def _get_redis() -> redis.Redis:
    """Get async Redis client"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            decode_responses=True
        )
    return redis.Redis(connection_pool=_redis_pool)


async def _submit_propensity_job(
    job_type: str,
    user_id: str,
    config: dict,
    dataset_id: Optional[str] = None,
    csv_content: Optional[str] = None,
    is_base64: bool = False,
) -> JobResponse:
    """Submit a propensity score analysis job to the queue

    Supports two modes:
    1. Dataset mode: dataset_id provided, data loaded from MinIO
    2. Direct mode: csv_content provided, data embedded in job
    """
    if not dataset_id and not csv_content:
        raise HTTPException(status_code=400, detail="Must provide either dataset_id or csv_content")

    if dataset_id and csv_content:
        raise HTTPException(status_code=400, detail="Provide either dataset_id or csv_content, not both")

    # Verify dataset exists (if using dataset mode)
    minio_path = None
    if dataset_id:
        dataset = await redis_dataset_store.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
        minio_path = dataset.get("minio_path")

    # Create job
    job_id = f"propensity-{uuid.uuid4().hex[:12]}"

    # Prepare params for worker
    params = {**config}
    if csv_content:
        # Decode base64 if needed
        if is_base64:
            csv_content = base64.b64decode(csv_content).decode('utf-8')
        params["csv_content"] = csv_content

    job_data = {
        "job_id": job_id,
        "job_type": job_type,
        "user_id": user_id,
        "dataset_id": dataset_id,
        "minio_path": minio_path,
        "params": params,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    # Get Redis client
    client = await _get_redis()

    # Save job metadata
    await client.set(
        f"{STATS_JOBS_PREFIX}{job_id}",
        json.dumps(job_data),
        ex=86400 * 7  # 7 days TTL
    )

    # Queue for processing
    await client.lpush(STATS_JOBS_PENDING, json.dumps(job_data))

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

    Supports two modes:
    - Dataset mode: Provide dataset_id for pre-uploaded data
    - Direct mode: Provide csv_content inline

    Model diagnostics include:
    - Pseudo R² (McFadden's)
    - C-statistic (AUC)
    - Brier score
    - Score overlap between groups

    Args:
        dataset_id: Dataset ID (optional, for pre-uploaded data)
        csv_content: CSV data as string (optional, for direct mode)
        treatment_column: Binary treatment (0/1)
        covariates: Variables to include in model
        method: logistic, gbm, or random_forest
        regularization: L2 penalty (for logistic)

    Returns:
        job_id for tracking
    """
    config = {
        "treatment_col": request.treatment_column,
        "covariates": request.covariates,
        "method": request.method,
        "regularization": request.regularization,
    }

    return await _submit_propensity_job(
        job_type="propensity_estimate",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
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
        dataset_id: Dataset ID (optional, for pre-uploaded data)
        csv_content: CSV data as string (optional, for direct mode)
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
        "treatment_col": request.treatment_column,
        "covariates": request.covariates,
        "score_col": request.score_column,
        "method": request.method,
        "caliper": request.caliper,
        "caliper_scale": request.caliper_scale,
        "replacement": request.replacement,
        "ratio": request.ratio,
    }

    return await _submit_propensity_job(
        job_type="propensity_match",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
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
        "treatment_col": request.treatment_column,
        "outcome_col": request.outcome_column,
        "covariates": request.covariates,
        "score_col": request.score_column,
        "method": request.method,
        "target": request.estimand.lower(),  # Worker uses 'target' not 'estimand'
    }

    return await _submit_propensity_job(
        job_type="propensity_effect",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
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
        "treatment_col": request.treatment_column,
        "covariates": request.covariates,
        "weights_column": request.weights_column,
        "matched_column": request.matched_column,
        "smd_threshold": request.threshold,
    }

    return await _submit_propensity_job(
        job_type="propensity_balance",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
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
        "treatment_col": request.treatment_column,
        "outcome_col": request.outcome_column,
        "covariates": request.covariates,
        "method": request.method,
        "caliper": request.caliper,
    }

    return await _submit_propensity_job(
        job_type="propensity_full",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
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

"""
Stats Service - ROC/AUC Analysis Routes

Routes for classifier evaluation:
- ROC curve computation
- AUC comparison (DeLong test)
- Optimal threshold selection
- Calibration analysis
- Full classifier evaluation

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
from pydantic import BaseModel, Field

from ..config import REDIS_DB, REDIS_HOST, REDIS_PORT, STATS_JOBS_PENDING, STATS_JOBS_PREFIX
from ..infrastructure.redis_dataset_store import redis_dataset_store

router = APIRouter(prefix="/roc", tags=["ROC/AUC Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ROCComputeRequest(BaseModel):
    """Request for ROC curve computation

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (for dataset mode)")
    csv_content: Optional[str] = Field(None, description="CSV data content (for direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    true_column: str = Field(..., description="True binary labels (0/1)")
    score_column: str = Field(..., description="Predicted probabilities or scores")
    pos_label: int = Field(default=1, description="Positive class label")
    n_bootstrap: int = Field(default=1000, description="Bootstrap iterations for CI")
    confidence_level: float = Field(default=0.95, description="Confidence level")
    generate_visualizations: bool = Field(default=True, description="Generate ROC curve plot")


class ROCCompareRequest(BaseModel):
    """Request for ROC curve comparison

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (for dataset mode)")
    csv_content: Optional[str] = Field(None, description="CSV data content (for direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    true_column: str = Field(..., description="True binary labels")
    score_columns: List[str] = Field(..., description="Multiple score columns to compare")
    model_names: Optional[List[str]] = Field(None, description="Names for each model")
    method: str = Field(default="delong", description="Comparison method: delong, bootstrap")
    generate_visualizations: bool = Field(default=True, description="Generate comparison plots")


class ThresholdRequest(BaseModel):
    """Request for optimal threshold analysis

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (for dataset mode)")
    csv_content: Optional[str] = Field(None, description="CSV data content (for direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    true_column: str = Field(..., description="True binary labels")
    score_column: str = Field(..., description="Predicted probabilities")
    method: str = Field(default="youden", description="Method: youden, f1, cost, sensitivity, specificity")
    cost_fp: float = Field(default=1.0, description="Cost of false positive (for cost method)")
    cost_fn: float = Field(default=1.0, description="Cost of false negative (for cost method)")
    min_sensitivity: Optional[float] = Field(None, description="Minimum sensitivity constraint")
    min_specificity: Optional[float] = Field(None, description="Minimum specificity constraint")


class CalibrationRequest(BaseModel):
    """Request for calibration analysis

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (for dataset mode)")
    csv_content: Optional[str] = Field(None, description="CSV data content (for direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    true_column: str = Field(..., description="True binary labels")
    score_column: str = Field(..., description="Predicted probabilities")
    n_bins: int = Field(default=10, description="Number of calibration bins")
    strategy: str = Field(default="uniform", description="Binning strategy: uniform, quantile")


class FullEvalRequest(BaseModel):
    """Request for full classifier evaluation

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    dataset_id: Optional[str] = Field(None, description="Dataset ID (for dataset mode)")
    csv_content: Optional[str] = Field(None, description="CSV data content (for direct mode)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    true_column: str = Field(..., description="True binary labels")
    score_column: str = Field(..., description="Predicted probabilities")
    threshold: Optional[float] = Field(None, description="Classification threshold (default: find optimal)")
    include_calibration: bool = Field(default=True, description="Include calibration analysis")
    include_precision_recall: bool = Field(default=True, description="Include PR curve")
    generate_visualizations: bool = Field(default=True, description="Generate all evaluation plots")


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


async def _submit_roc_job(
    job_type: str,
    user_id: str,
    config: dict,
    dataset_id: Optional[str] = None,
    csv_content: Optional[str] = None,
    is_base64: bool = False,
) -> JobResponse:
    """Submit a ROC analysis job to the queue

    Supports dual-mode:
    - Dataset mode: Provide dataset_id (pre-uploaded data)
    - Direct mode: Provide csv_content (inline data)
    """
    # Validate: must provide either dataset_id OR csv_content
    if not dataset_id and not csv_content:
        raise HTTPException(
            status_code=400,
            detail="Must provide either dataset_id or csv_content"
        )

    # Dataset mode: verify dataset exists
    minio_path = None
    if dataset_id:
        dataset = await redis_dataset_store.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
        minio_path = dataset.get("minio_path")

    # Create job
    job_id = f"roc-{uuid.uuid4().hex[:12]}"

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
        message=f"ROC {job_type} job submitted successfully",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/compute/submit", response_model=JobResponse)
async def submit_roc_compute_job(request: ROCComputeRequest):
    """
    📈 Submit ROC curve computation job.

    Computes ROC curve and related metrics:
    - FPR, TPR at multiple thresholds
    - AUC with confidence interval (bootstrap or DeLong)
    - Partial AUC at specific FPR ranges

    Args:
        true_column: Binary true labels (0/1)
        score_column: Predicted probabilities
        n_bootstrap: Iterations for CI estimation
        confidence_level: CI level (default 0.95)

    Returns:
        ROC curve points, AUC, CI, optimal threshold
    """
    config = {
        "y_true_col": request.true_column,
        "y_score_col": request.score_column,
        "pos_label": request.pos_label,
        "n_bootstrap": request.n_bootstrap,
        "confidence_level": request.confidence_level,
        "generate_visualizations": request.generate_visualizations,
    }

    return await _submit_roc_job(
        job_type="roc_compute",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
    )


@router.post("/compare/submit", response_model=JobResponse)
async def submit_roc_compare_job(request: ROCCompareRequest):
    """
    🔬 Submit ROC curves comparison job.

    Compares AUC between multiple models using:
    - DeLong test: Non-parametric, accounts for correlation
    - Bootstrap: More flexible, handles complex cases

    Output includes:
    - AUC for each model
    - Pairwise AUC differences with CI
    - P-values for statistical significance
    - Overlay plot data
    """
    config = {
        "y_true_col": request.true_column,
        "model_score_cols": request.score_columns,
        "model_names": request.model_names or [f"Model_{i+1}" for i in range(len(request.score_columns))],
        "method": request.method,
        "generate_visualizations": request.generate_visualizations,
    }

    return await _submit_roc_job(
        job_type="roc_compare",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
    )


@router.post("/threshold/submit", response_model=JobResponse)
async def submit_threshold_analysis_job(request: ThresholdRequest):
    """
    🎯 Submit optimal threshold analysis job.

    Finds best classification threshold based on criterion:

    Methods:
    - youden: Maximize Sensitivity + Specificity - 1
    - f1: Maximize F1 score
    - cost: Minimize FP×cost_fp + FN×cost_fn
    - sensitivity: Highest threshold meeting min_sensitivity
    - specificity: Lowest threshold meeting min_specificity

    Output includes:
    - Optimal threshold
    - Metrics at optimal threshold
    - Sensitivity vs specificity plot data
    - Threshold vs metric curves
    """
    config = {
        "y_true_col": request.true_column,
        "y_score_col": request.score_column,
        "method": request.method,
        "cost_fp": request.cost_fp,
        "cost_fn": request.cost_fn,
        "min_sensitivity": request.min_sensitivity,
        "min_specificity": request.min_specificity,
    }

    return await _submit_roc_job(
        job_type="roc_threshold",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
    )


@router.post("/calibration/submit", response_model=JobResponse)
async def submit_calibration_job(request: CalibrationRequest):
    """
    📊 Submit calibration analysis job.

    Assesses how well predicted probabilities match actual frequencies.

    Metrics:
    - Brier score (lower is better)
    - Expected Calibration Error (ECE)
    - Maximum Calibration Error (MCE)
    - Hosmer-Lemeshow test

    Output includes:
    - Calibration curve data
    - Reliability diagram
    - Bin-wise statistics
    """
    config = {
        "y_true_col": request.true_column,
        "y_score_col": request.score_column,
        "n_bins": request.n_bins,
        "strategy": request.strategy,
    }

    return await _submit_roc_job(
        job_type="roc_calibration",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
    )


@router.post("/full-eval/submit", response_model=JobResponse)
async def submit_full_evaluation_job(request: FullEvalRequest):
    """
    🚀 Submit comprehensive classifier evaluation job.

    Complete evaluation including:
    1. ROC curve and AUC with CI
    2. Optimal threshold selection
    3. Confusion matrix and derived metrics
    4. Precision-Recall curve and AUPRC
    5. Calibration analysis (optional)
    6. Lift and gain charts

    Perfect for final model assessment and reporting.
    """
    config = {
        "y_true_col": request.true_column,
        "y_score_col": request.score_column,
        "threshold": request.threshold,
        "include_calibration": request.include_calibration,
        "include_precision_recall": request.include_precision_recall,
        "generate_visualizations": request.generate_visualizations,
    }

    return await _submit_roc_job(
        job_type="roc_full_eval",
        user_id=request.user_id,
        config=config,
        dataset_id=request.dataset_id,
        csv_content=request.csv_content,
        is_base64=request.is_base64,
    )


@router.get("/methods")
async def get_roc_methods():
    """
    📋 Get available ROC/AUC methods and their descriptions.
    """
    return {
        "threshold_methods": {
            "youden": {
                "name": "Youden's J statistic",
                "formula": "J = Sensitivity + Specificity - 1",
                "best_for": "Balanced sensitivity/specificity",
            },
            "f1": {
                "name": "F1 Score",
                "formula": "F1 = 2 × (Precision × Recall) / (Precision + Recall)",
                "best_for": "Imbalanced classes, focus on positive class",
            },
            "cost": {
                "name": "Cost-based",
                "formula": "Minimize: FP × cost_fp + FN × cost_fn",
                "best_for": "When misclassification costs differ",
            },
            "sensitivity": {
                "name": "Sensitivity constrained",
                "description": "Highest threshold meeting minimum sensitivity",
                "best_for": "When missing positives is critical (e.g., disease screening)",
            },
            "specificity": {
                "name": "Specificity constrained",
                "description": "Lowest threshold meeting minimum specificity",
                "best_for": "When false alarms are costly (e.g., confirmatory tests)",
            },
        },
        "comparison_methods": {
            "delong": {
                "name": "DeLong Test",
                "description": "Non-parametric comparison of correlated AUCs",
                "reference": "DeLong et al., 1988",
            },
            "bootstrap": {
                "name": "Bootstrap",
                "description": "Resampling-based comparison",
                "pros": "More flexible, handles complex scenarios",
            },
        },
        "calibration_metrics": {
            "brier_score": "Mean squared error of probability estimates",
            "ece": "Expected Calibration Error - weighted average calibration gap",
            "mce": "Maximum Calibration Error - worst bin calibration gap",
            "hosmer_lemeshow": "Chi-square test for calibration",
        },
    }

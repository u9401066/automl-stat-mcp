"""
Stats Service - EDA Routes (DDD)

Routes for Exploratory Data Analysis using ydata-profiling.
Refactored to use Domain-Driven Design with Use Cases.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..application.dto import SubmitEDARequest as SubmitEDADTO
from ..application.use_cases import DatasetNotFoundError, SubmitEDAUseCase
from ..infrastructure.redis_dataset_store import redis_dataset_store
from ..infrastructure.repositories import get_job_queue, get_job_repository

router = APIRouter(prefix="/eda", tags=["EDA"])


class EDARequest(BaseModel):
    """Request model for EDA job submission"""
    dataset_id: str = Field(..., description="Dataset ID in MinIO")
    user_id: str = Field(..., description="User ID for isolation")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    title: Optional[str] = Field("EDA Report", description="Report title")
    minimal: Optional[bool] = Field(True, description="Use minimal mode for faster processing")


class EDAResponse(BaseModel):
    """Response model for EDA job submission"""
    job_id: str
    job_type: str
    status: str
    message: str


def _get_submit_use_case() -> SubmitEDAUseCase:
    """Dependency injection for submit use case"""
    return SubmitEDAUseCase(
        job_repo=get_job_repository(),
        dataset_store=redis_dataset_store,
        job_queue=get_job_queue(),
    )


@router.post("/submit", response_model=EDAResponse)
async def submit_eda_job(request: EDARequest):
    """
    Submit an EDA job.

    This will generate a comprehensive data profiling report using ydata-profiling.
    The job runs asynchronously - use /jobs/{job_id} to check status.

    Returns:
        EDAResponse with job_id for tracking
    """
    use_case = _get_submit_use_case()

    try:
        result = await use_case.execute(
            SubmitEDADTO(
                dataset_id=request.dataset_id,
                user_id=request.user_id,
                session_id=request.session_id,
                title=request.title or "EDA Report",
                minimal=request.minimal if request.minimal is not None else True,
            )
        )

        return EDAResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            message=result.message,
        )

    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# TODO: Fix preview_dataset endpoint - minio_client needs to be imported
# This endpoint is currently disabled due to missing dependencies
"""
@router.post("/preview")
async def preview_dataset(
    dataset_id: str,
    n_rows: int = Query(default=10, le=100)
):
    \"\"\"
    Preview dataset before running EDA.

    Returns first N rows and basic statistics.
    \"\"\"
    # First check if dataset exists in Redis store
    dataset_info = redis_dataset_store.get_dataset(dataset_id)
    if not dataset_info:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found. Please register it first."
        )

    # Load preview from MinIO
    minio_path = dataset_info.get("minio_path")
    df = minio_client.load_dataset_by_path(minio_path, n_rows=n_rows)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found at {minio_path}"
        )

    return {
        "dataset_id": dataset_id,
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "preview": df.to_dict(orient="records"),
        "missing_values": df.isnull().sum().to_dict(),
    }
"""

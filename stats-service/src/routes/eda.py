"""
Stats Service - EDA Routes

Routes for Exploratory Data Analysis using ydata-profiling.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from ..infrastructure.redis_client import redis_client
from ..infrastructure.minio_client import minio_client

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


@router.post("/submit", response_model=EDAResponse)
async def submit_eda_job(request: EDARequest):
    """
    Submit an EDA job.
    
    This will generate a comprehensive data profiling report using ydata-profiling.
    The job runs asynchronously - use /jobs/{job_id} to check status.
    
    Returns:
        EDAResponse with job_id for tracking
    """
    # Verify dataset exists
    dataset_info = minio_client.get_dataset_info(request.dataset_id)
    if not dataset_info:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {request.dataset_id} not found in storage"
        )
    
    # Create job
    job = await redis_client.create_job(
        job_type="eda",
        params={
            "dataset_id": request.dataset_id,
            "title": request.title,
            "minimal": request.minimal,
        },
        user_id=request.user_id,
        session_id=request.session_id
    )
    
    return EDAResponse(
        job_id=job["job_id"],
        job_type="eda",
        status="pending",
        message="EDA job submitted successfully. Use /jobs/{job_id} to check status."
    )


@router.post("/preview")
async def preview_dataset(
    dataset_id: str,
    n_rows: int = Query(default=10, le=100)
):
    """
    Preview dataset before running EDA.
    
    Returns first N rows and basic statistics.
    """
    df = minio_client.load_dataset_preview(dataset_id, n_rows=n_rows)
    
    if df is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found"
        )
    
    return {
        "dataset_id": dataset_id,
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "preview": df.to_dict(orient="records"),
        "missing_values": df.isnull().sum().to_dict(),
    }

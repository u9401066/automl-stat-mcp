"""
Stats Service - TableOne Routes (DDD)

Routes for generating Table 1 (descriptive statistics) using tableone package.
Refactored to use Domain-Driven Design with Use Cases.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..application.dto import SubmitTableOneRequest as SubmitTableOneDTO
from ..application.use_cases import DatasetNotFoundError, SubmitTableOneUseCase
from ..infrastructure.minio_client import minio_client
from ..infrastructure.redis_dataset_store import redis_dataset_store
from ..infrastructure.repositories import get_job_queue, get_job_repository

router = APIRouter(prefix="/tableone", tags=["TableOne"])


class TableOneRequest(BaseModel):
    """Request model for TableOne job submission"""
    dataset_id: str = Field(..., description="Dataset ID in MinIO")
    user_id: str = Field(..., description="User ID for isolation")
    session_id: Optional[str] = Field(None, description="Optional session ID")

    # TableOne specific parameters
    columns: Optional[List[str]] = Field(None, description="Columns to include (all if not specified)")
    categorical: Optional[List[str]] = Field(None, description="Categorical columns")
    continuous: Optional[List[str]] = Field(None, description="Continuous columns")
    groupby: Optional[str] = Field(None, description="Column to group by for stratified analysis")
    nonnormal: Optional[List[str]] = Field(None, description="Non-normally distributed columns (use median/IQR)")
    pval: Optional[bool] = Field(False, description="Calculate p-values between groups")


class TableOneResponse(BaseModel):
    """Response model for TableOne job submission"""
    job_id: str
    job_type: str
    status: str
    message: str


def _get_submit_use_case() -> SubmitTableOneUseCase:
    """Dependency injection for submit use case"""
    return SubmitTableOneUseCase(
        job_repo=get_job_repository(),
        dataset_store=redis_dataset_store,
        job_queue=get_job_queue(),
    )


@router.post("/submit", response_model=TableOneResponse)
async def submit_tableone_job(request: TableOneRequest):
    """
    Submit a TableOne job.

    This will generate a publication-ready Table 1 with descriptive statistics.
    The job runs asynchronously - use /jobs/{job_id} to check status.

    Parameters:
        - columns: Specify which columns to include
        - categorical: Columns to treat as categorical
        - groupby: Stratify by this column (e.g., treatment group)
        - nonnormal: Use median/IQR instead of mean/SD for these columns
        - pval: Include p-values for group comparisons

    Returns:
        TableOneResponse with job_id for tracking
    """
    use_case = _get_submit_use_case()

    try:
        result = await use_case.execute(
            SubmitTableOneDTO(
                dataset_id=request.dataset_id,
                user_id=request.user_id,
                session_id=request.session_id,
                columns=request.columns,
                categorical=request.categorical,
                continuous=request.continuous,
                groupby=request.groupby,
                nonnormal=request.nonnormal,
                pval=request.pval if request.pval is not None else False,
            )
        )

        return TableOneResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            message=result.message,
        )

    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/columns")
async def get_column_suggestions(dataset_id: str, user_id: str):
    """
    Get column type suggestions for TableOne configuration.

    Analyzes the dataset and suggests which columns are likely
    categorical vs continuous.
    """
    # Check dataset exists
    dataset_info = redis_dataset_store.get_dataset(dataset_id)
    if not dataset_info:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found. Please register it first."
        )

    # Load preview from MinIO
    minio_path = dataset_info.get("minio_path")
    if not minio_path:
        raise HTTPException(status_code=400, detail="MinIO path not found in dataset info")

    df = minio_client.load_dataset_by_path(minio_path, n_rows=1000)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found at {minio_path}"
        )

    categorical = []
    continuous = []
    datetime_cols = []

    for col in df.columns:
        dtype = df[col].dtype

        # Skip ID-like columns
        if col.lower() in ['id', 'index', 'row_id', 'record_id']:
            continue

        # Datetime columns
        if 'datetime' in str(dtype):
            datetime_cols.append(col)
        # Categorical: object dtype or few unique values
        elif dtype == 'object' or df[col].nunique() < 10:
            categorical.append(col)
        # Continuous: numeric types
        elif 'int' in str(dtype) or 'float' in str(dtype):
            continuous.append(col)

    # Suggest nonnormal based on simple heuristic
    nonnormal_suggestions = []
    for col in continuous:
        # If skewness is high, suggest nonnormal
        if df[col].skew() > 1.0:
            nonnormal_suggestions.append(col)

    # Suggest groupby columns (categorical with 2-5 groups)
    groupby_suggestions = [
        col for col in categorical
        if 2 <= df[col].nunique() <= 5
    ]

    return {
        "dataset_id": dataset_id,
        "suggestions": {
            "categorical": categorical,
            "continuous": continuous,
            "datetime": datetime_cols,
            "nonnormal": nonnormal_suggestions,
            "groupby": groupby_suggestions,
        },
        "total_columns": len(df.columns),
        "sample_size": len(df),
    }

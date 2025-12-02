"""
FastAPI Router - Training endpoints (Redis Queue based)

Jobs are submitted to Redis and processed by the worker container.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Header

from ..schemas import (
    AutoMLTrainRequest, SpecificTrainRequest, CompareModelsRequest,
    JobResponse, ErrorResponse,
)
from ..dependencies import get_container
from ....domain.models import DatasetId, ProblemType, TrainingConfig, JobType

router = APIRouter(prefix="/train", tags=["Training"])


@router.post(
    "/automl",
    response_model=JobResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def submit_automl_job(
    request: AutoMLTrainRequest,
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    Submit an AutoML training job.
    
    This will automatically search for the best model and hyperparameters.
    Returns a job ID that can be used to track progress.
    
    The job is queued and processed by the AutoGluon worker container.
    """
    container = get_container()
    
    try:
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await container.dataset_repo.get_by_id(dataset_id)
        
        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")
        
        if not dataset.belongs_to(x_user_id, x_session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column exists
        if not dataset.has_column(request.target_column):
            raise ValueError(
                f"Target column '{request.target_column}' not found in dataset"
            )

        # 3. Create training config
        config = TrainingConfig.for_automl(
            dataset_id=request.dataset_id,
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            time_limit=request.time_limit,
            presets=request.presets,
            metric=request.metric,
        )

        # 4. Submit to Redis queue
        job = container.job_queue.submit_job(
            job_type=JobType.AUTOML,
            user_id=x_user_id,
            session_id=x_session_id,
            config=config,
            dataset_minio_path=dataset.minio_path,
        )
        
        return JobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=0.0,
            status_message="Queued for processing",
            created_at=job.created_at.isoformat(),
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post(
    "/specific",
    response_model=JobResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def submit_specific_train_job(
    request: SpecificTrainRequest,
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    Submit a training job with specific algorithms.
    
    Use this when you want to train specific model types.
    Available algorithms: GBM, CAT, XGB, RF, XT, KNN, LR, NN_TORCH, FASTAI
    """
    container = get_container()
    
    try:
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await container.dataset_repo.get_by_id(dataset_id)
        
        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")
        
        if not dataset.belongs_to(x_user_id, x_session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column
        if not dataset.has_column(request.target_column):
            raise ValueError(
                f"Target column '{request.target_column}' not found in dataset"
            )

        # 3. Create training config
        config = TrainingConfig.for_specific_algorithms(
            dataset_id=request.dataset_id,
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            algorithms=request.algorithms,
            time_limit=request.time_limit,
        )

        # 4. Submit to Redis queue
        job = container.job_queue.submit_job(
            job_type=JobType.SPECIFIC,
            user_id=x_user_id,
            session_id=x_session_id,
            config=config,
            dataset_minio_path=dataset.minio_path,
        )
        
        return JobResponse(
            job_id=job.id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress=0.0,
            status_message="Queued for processing",
            created_at=job.created_at.isoformat(),
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post(
    "/compare",
    response_model=JobResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def submit_compare_job(
    request: CompareModelsRequest,
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    Submit a job to compare multiple algorithms.
    
    This trains multiple models and returns a leaderboard comparing their performance.
    Requires at least 2 algorithms.
    """
    container = get_container()
    
    try:
        # Validate at least 2 algorithms
        if len(request.algorithms) < 2:
            raise ValueError("Compare requires at least 2 algorithms")
        
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await container.dataset_repo.get_by_id(dataset_id)
        
        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")
        
        if not dataset.belongs_to(x_user_id, x_session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column
        if not dataset.has_column(request.target_column):
            raise ValueError(
                f"Target column '{request.target_column}' not found in dataset"
            )

        # 3. Create training config
        config = TrainingConfig.for_comparison(
            dataset_id=request.dataset_id,
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            algorithms=request.algorithms,
            time_limit=request.time_limit,
        )

        # 4. Submit to Redis queue
        job = container.job_queue.submit_job(
            job_type=JobType.COMPARE,
            user_id=x_user_id,
            session_id=x_session_id,
            config=config,
            dataset_minio_path=dataset.minio_path,
        )
        
        return JobResponse(
            job_id=job.id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress=0.0,
            status_message="Queued for processing",
            created_at=job.created_at.isoformat(),
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

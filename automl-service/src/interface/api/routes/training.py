"""
FastAPI Router - Training endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Header

from ..schemas import (
    AutoMLTrainRequest, SpecificTrainRequest, CompareModelsRequest,
    JobResponse, ErrorResponse,
)
from ..dependencies import get_container
from ....application.use_cases import (
    SubmitAutoMLJobUseCase,
    SubmitSpecificTrainJobUseCase,
    SubmitCompareJobUseCase,
    GetJobStatusUseCase,
)
from ....application.dto import (
    AutoMLTrainRequest as AutoMLTrainDTO,
    SpecificTrainRequest as SpecificTrainDTO,
    CompareModelsRequest as CompareModelsDTO,
)

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
    """
    container = get_container()
    
    use_case = SubmitAutoMLJobUseCase(
        dataset_repo=container.dataset_repo,
        job_repo=container.job_repo,
    )
    
    try:
        result = await use_case.execute(
            AutoMLTrainDTO(
                dataset_id=request.dataset_id,
                target_column=request.target_column,
                problem_type=request.problem_type,
                user_id=x_user_id,
                session_id=x_session_id,
                time_limit=request.time_limit,
                presets=request.presets,
                metric=request.metric,
            )
        )
        
        return JobResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            progress=result.progress,
            status_message=result.status_message,
            created_at=result.created_at,
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
    
    use_case = SubmitSpecificTrainJobUseCase(
        dataset_repo=container.dataset_repo,
        job_repo=container.job_repo,
    )
    
    try:
        result = await use_case.execute(
            SpecificTrainDTO(
                dataset_id=request.dataset_id,
                target_column=request.target_column,
                problem_type=request.problem_type,
                algorithms=request.algorithms,
                user_id=x_user_id,
                session_id=x_session_id,
                time_limit=request.time_limit,
                hyperparameters=request.hyperparameters,
            )
        )
        
        return JobResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            progress=result.progress,
            status_message=result.status_message,
            created_at=result.created_at,
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
    
    use_case = SubmitCompareJobUseCase(
        dataset_repo=container.dataset_repo,
        job_repo=container.job_repo,
    )
    
    try:
        result = await use_case.execute(
            CompareModelsDTO(
                dataset_id=request.dataset_id,
                target_column=request.target_column,
                problem_type=request.problem_type,
                algorithms=request.algorithms,
                user_id=x_user_id,
                session_id=x_session_id,
                time_limit=request.time_limit,
            )
        )
        
        return JobResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            progress=result.progress,
            status_message=result.status_message,
            created_at=result.created_at,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

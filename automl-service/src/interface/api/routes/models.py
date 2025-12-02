"""
FastAPI Router - Model endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header

from ..schemas import (
    ModelResponse, LeaderboardEntryResponse, 
    PredictRequest, PredictResponse, ErrorResponse,
)
from ..dependencies import get_container
from ....application.model_use_cases import (
    ListModelsUseCase,
    GetModelLeaderboardUseCase,
    PredictUseCase,
    DeleteModelUseCase,
)
from ....application.dto import PredictRequest as PredictDTO

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "",
    response_model=List[ModelResponse],
)
async def list_models(
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    List all trained models for the current user/session.
    """
    container = get_container()
    
    use_case = ListModelsUseCase(model_repo=container.model_repo)
    
    results = await use_case.execute(x_user_id, x_session_id)
    
    return [
        ModelResponse(
            model_id=r.model_id,
            name=r.name,
            problem_type=r.problem_type,
            target_column=r.target_column,
            best_model_name=r.best_model_name,
            best_score=r.best_score,
            metric=r.metric,
            algorithms_used=r.algorithms_used,
            leaderboard=[
                LeaderboardEntryResponse(
                    model_name=e.model_name,
                    score=e.score,
                    fit_time=e.fit_time,
                    pred_time=e.pred_time,
                    stack_level=e.stack_level,
                )
                for e in r.leaderboard
            ],
            feature_importance=r.feature_importance,
            created_at=r.created_at,
        )
        for r in results
    ]


@router.get(
    "/{model_id}/leaderboard",
    response_model=List[LeaderboardEntryResponse],
    responses={404: {"model": ErrorResponse}},
)
async def get_model_leaderboard(
    model_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Get the leaderboard for a trained model.
    
    Shows performance comparison of all models trained during the experiment.
    """
    container = get_container()
    
    use_case = GetModelLeaderboardUseCase(model_repo=container.model_repo)
    
    try:
        results = await use_case.execute(model_id, x_user_id)
        
        return [
            LeaderboardEntryResponse(
                model_name=r.model_name,
                score=r.score,
                fit_time=r.fit_time,
                pred_time=r.pred_time,
                stack_level=r.stack_level,
            )
            for r in results
        ]
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post(
    "/predict",
    response_model=PredictResponse,
    responses={404: {"model": ErrorResponse}},
)
async def predict(
    request: PredictRequest,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Make predictions using a trained model.
    
    The prediction dataset should have the same features as the training dataset
    (excluding the target column).
    """
    container = get_container()
    
    use_case = PredictUseCase(
        model_repo=container.model_repo,
        dataset_repo=container.dataset_repo,
        ml_engine=container.ml_engine,
        file_storage=container.file_storage,
    )
    
    try:
        result = await use_case.execute(
            PredictDTO(
                model_id=request.model_id,
                dataset_id=request.dataset_id,
                user_id=x_user_id,
            )
        )
        
        return PredictResponse(
            model_id=result.model_id,
            predictions=result.predictions,
            probabilities=result.probabilities,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete(
    "/{model_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
)
async def delete_model(
    model_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """Delete a trained model."""
    container = get_container()
    
    use_case = DeleteModelUseCase(model_repo=container.model_repo)
    
    try:
        await use_case.execute(model_id, x_user_id)
        return {"message": "Model deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

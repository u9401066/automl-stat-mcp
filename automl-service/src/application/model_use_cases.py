"""
Model Use Cases - For model management and prediction
"""
from typing import List, Optional

from ..domain.models import (
    DatasetId,
    ModelId,
)
from ..domain.repositories import DatasetRepository, ModelRepository
from ..domain.services import FileStorageService, MLEngineService
from .dto import (
    LeaderboardEntryResponse,
    ModelResponse,
    PredictRequest,
    PredictResponse,
)


class ListModelsUseCase:
    """Use case for listing user's models"""

    def __init__(self, model_repo: ModelRepository):
        self.model_repo = model_repo

    async def execute(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[ModelResponse]:
        models = await self.model_repo.find_by_user(user_id, session_id)

        return [
            ModelResponse(
                model_id=str(m.id),
                name=m.name,
                problem_type=m.problem_type,
                target_column=m.target_column,
                best_model_name=m.best_model_name,
                best_score=m.best_score,
                metric=m.metric,
                algorithms_used=m.algorithms_used,
                leaderboard=[
                    LeaderboardEntryResponse(
                        model_name=e.model_name,
                        score=e.score,
                        fit_time=e.fit_time,
                        pred_time=e.pred_time,
                        stack_level=e.stack_level,
                    )
                    for e in m.leaderboard
                ],
                feature_importance=m.feature_importance,
                created_at=m.created_at.isoformat(),
            )
            for m in models
        ]


class GetModelLeaderboardUseCase:
    """Use case for getting model's leaderboard"""

    def __init__(self, model_repo: ModelRepository):
        self.model_repo = model_repo

    async def execute(
        self,
        model_id: str,
        user_id: str
    ) -> List[LeaderboardEntryResponse]:
        model_id_obj = ModelId.from_string(model_id)
        model = await self.model_repo.get_by_id(model_id_obj)

        if not model:
            raise ValueError(f"Model not found: {model_id}")

        if not model.belongs_to(user_id):
            raise PermissionError("Access denied to model")

        return [
            LeaderboardEntryResponse(
                model_name=e.model_name,
                score=e.score,
                fit_time=e.fit_time,
                pred_time=e.pred_time,
                stack_level=e.stack_level,
            )
            for e in model.leaderboard
        ]


class PredictUseCase:
    """Use case for making predictions"""

    def __init__(
        self,
        model_repo: ModelRepository,
        dataset_repo: DatasetRepository,
        ml_engine: MLEngineService,
        file_storage: FileStorageService,
    ):
        self.model_repo = model_repo
        self.dataset_repo = dataset_repo
        self.ml_engine = ml_engine
        self.file_storage = file_storage

    async def execute(self, request: PredictRequest) -> PredictResponse:
        # 1. Get model
        model_id = ModelId.from_string(request.model_id)
        model = await self.model_repo.get_by_id(model_id)

        if not model:
            raise ValueError(f"Model not found: {request.model_id}")

        if not model.belongs_to(request.user_id):
            raise PermissionError("Access denied to model")

        # 2. Get dataset
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await self.dataset_repo.get_by_id(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")

        if not dataset.belongs_to(request.user_id):
            raise PermissionError("Access denied to dataset")

        # 3. Load data from MinIO
        data = await self.file_storage.read_csv(dataset.minio_path)

        # 4. Make predictions
        predictions = await self.ml_engine.predict(model.model_path, data)

        # 5. Get probabilities if classification
        probabilities = None
        if model.problem_type in ("binary", "multiclass"):
            try:
                probabilities = await self.ml_engine.predict_proba(
                    model.model_path, data
                )
            except Exception:
                pass  # Some models may not support predict_proba

        return PredictResponse(
            model_id=request.model_id,
            predictions=predictions,
            probabilities=probabilities,
        )


class DeleteModelUseCase:
    """Use case for deleting a model"""

    def __init__(self, model_repo: ModelRepository):
        self.model_repo = model_repo

    async def execute(self, model_id: str, user_id: str) -> bool:
        model_id_obj = ModelId.from_string(model_id)
        model = await self.model_repo.get_by_id(model_id_obj)

        if not model:
            raise ValueError(f"Model not found: {model_id}")

        if not model.belongs_to(user_id):
            raise PermissionError("Access denied to model")

        return await self.model_repo.delete(model_id_obj)

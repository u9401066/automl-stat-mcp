"""
AutoGluon ML Engine Implementation
"""
from typing import Any, Dict, List, Tuple, Callable, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from pathlib import Path

from ..domain.services import MLEngineService
from ..domain.models import TrainingConfig, LeaderboardEntry
from ..config import MODELS_DIR


# Thread pool for running AutoGluon (which is synchronous)
_executor = ThreadPoolExecutor(max_workers=4)


class AutoGluonEngine(MLEngineService):
    """AutoGluon implementation of MLEngineService"""

    def __init__(self):
        # Lazy import to avoid loading AutoGluon until needed
        self._predictor_cache: Dict[str, Any] = {}

    def _get_task(self, problem_type: str) -> str:
        """Convert problem type to AutoGluon task"""
        mapping = {
            "binary": "binary",
            "multiclass": "multiclass",
            "regression": "regression",
        }
        return mapping.get(problem_type, "binary")

    async def train(
        self,
        data: pd.DataFrame,
        config: TrainingConfig,
        model_save_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float, List[LeaderboardEntry], Dict[str, float]]:
        """Train using AutoGluon"""
        
        def _train_sync():
            from autogluon.tabular import TabularPredictor
            
            # Create predictor
            predictor = TabularPredictor(
                label=config.target_column,
                path=model_save_path,
                problem_type=self._get_task(config.problem_type),
                eval_metric=config.get_metric(),
            )
            
            # Get hyperparameters
            hyperparameters = config.get_hyperparameters()
            
            # Train
            predictor.fit(
                train_data=data,
                time_limit=config.time_limit,
                presets=config.presets,
                hyperparameters=hyperparameters,
                verbosity=1,
            )
            
            # Get results
            leaderboard_df = predictor.leaderboard(silent=True)
            
            leaderboard = []
            for _, row in leaderboard_df.iterrows():
                leaderboard.append(LeaderboardEntry(
                    model_name=row["model"],
                    score=float(row["score_val"]),
                    fit_time=float(row.get("fit_time", 0)),
                    pred_time=float(row.get("pred_time_val", 0)),
                    stack_level=int(row.get("stack_level", 0)),
                ))
            
            # Get best model info
            best_model_name = predictor.get_model_best()
            best_score = float(leaderboard_df.iloc[0]["score_val"]) if len(leaderboard_df) > 0 else 0.0
            
            # Get feature importance
            try:
                importance_df = predictor.feature_importance(data, silent=True)
                feature_importance = importance_df["importance"].to_dict()
            except Exception:
                feature_importance = {}
            
            return best_model_name, best_score, leaderboard, feature_importance

        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _train_sync)
        
        return result

    async def predict(
        self,
        model_path: str,
        data: pd.DataFrame,
    ) -> List[Any]:
        """Make predictions using trained model"""
        
        def _predict_sync():
            from autogluon.tabular import TabularPredictor
            
            # Load predictor
            if model_path in self._predictor_cache:
                predictor = self._predictor_cache[model_path]
            else:
                predictor = TabularPredictor.load(model_path)
                self._predictor_cache[model_path] = predictor
            
            predictions = predictor.predict(data)
            return predictions.tolist()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _predict_sync)

    async def predict_proba(
        self,
        model_path: str,
        data: pd.DataFrame,
    ) -> List[List[float]]:
        """Get prediction probabilities"""
        
        def _predict_proba_sync():
            from autogluon.tabular import TabularPredictor
            
            # Load predictor
            if model_path in self._predictor_cache:
                predictor = self._predictor_cache[model_path]
            else:
                predictor = TabularPredictor.load(model_path)
                self._predictor_cache[model_path] = predictor
            
            proba = predictor.predict_proba(data)
            return proba.values.tolist()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _predict_proba_sync)

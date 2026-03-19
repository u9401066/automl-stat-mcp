"""
MLModel - Aggregate Root for trained machine learning models
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ModelId:
    """Value Object for Model identifier"""
    value: UUID

    @classmethod
    def generate(cls) -> "ModelId":
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "ModelId":
        return cls(value=UUID(id_str))

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class LeaderboardEntry:
    """Value Object for a single model in the leaderboard"""
    model_name: str
    score: float
    fit_time: float
    pred_time: float
    stack_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "score": self.score,
            "fit_time": self.fit_time,
            "pred_time": self.pred_time,
            "stack_level": self.stack_level,
        }


@dataclass
class MLModel:
    """
    MLModel Aggregate Root

    Represents a trained AutoGluon model (which may include ensemble).
    """
    id: ModelId
    name: str
    user_id: str
    dataset_id: str  # Reference to the training dataset

    # Model info
    problem_type: str  # "binary", "multiclass", "regression"
    target_column: str
    model_path: str  # Local path to saved model

    # Training results
    best_model_name: str = ""
    best_score: float = 0.0
    metric: str = "accuracy"
    leaderboard: List[LeaderboardEntry] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)

    # Configuration used
    algorithms_used: List[str] = field(default_factory=list)
    time_limit: int = 300
    presets: str = "medium_quality"

    # Metadata
    session_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def set_training_results(
        self,
        best_model_name: str,
        best_score: float,
        metric: str,
        leaderboard: List[LeaderboardEntry],
        feature_importance: Dict[str, float],
    ) -> None:
        """Set results after training completes"""
        self.best_model_name = best_model_name
        self.best_score = best_score
        self.metric = metric
        self.leaderboard = leaderboard
        self.feature_importance = feature_importance

    def get_leaderboard_dict(self) -> List[Dict[str, Any]]:
        """Get leaderboard as list of dicts"""
        return [entry.to_dict() for entry in self.leaderboard]

    def belongs_to(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Check if model belongs to user/session"""
        if self.user_id != user_id:
            return False
        if session_id and self.session_id and self.session_id != session_id:
            return False
        return True

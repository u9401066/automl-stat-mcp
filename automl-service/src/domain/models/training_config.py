"""
TrainingConfig - Value Object for training configuration
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class ProblemType(str, Enum):
    """Machine learning problem type"""
    BINARY = "binary"
    MULTICLASS = "multiclass"
    REGRESSION = "regression"


@dataclass(frozen=True)
class TrainingConfig:
    """
    Training Configuration Value Object
    
    Immutable configuration for a training job.
    """
    target_column: str
    problem_type: ProblemType
    
    # Algorithm selection
    algorithms: Optional[List[str]] = None  # None = use all (AutoML)
    hyperparameters: Optional[Dict[str, Any]] = None  # Custom hyperparams
    
    # Training settings
    time_limit: int = 300  # seconds
    presets: str = "medium_quality"  # AutoGluon presets
    metric: Optional[str] = None  # Auto-select if None
    
    # Validation
    num_folds: int = 5
    holdout_frac: Optional[float] = None
    
    # Resource limits
    num_cpus: Optional[int] = None
    num_gpus: Optional[int] = None

    def get_metric(self) -> str:
        """Get the evaluation metric based on problem type"""
        if self.metric:
            return self.metric
        
        # Default metrics by problem type
        defaults = {
            ProblemType.BINARY: "roc_auc",
            ProblemType.MULTICLASS: "accuracy",
            ProblemType.REGRESSION: "root_mean_squared_error",
        }
        return defaults.get(self.problem_type, "accuracy")

    def get_hyperparameters(self) -> Dict[str, Any]:
        """Get hyperparameters dict for AutoGluon"""
        if self.hyperparameters:
            return self.hyperparameters
        
        if self.algorithms:
            # Use specified algorithms with default hyperparams
            return {algo: {} for algo in self.algorithms}
        
        # Return None for full AutoML
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "target_column": self.target_column,
            "problem_type": self.problem_type.value,
            "algorithms": self.algorithms,
            "time_limit": self.time_limit,
            "presets": self.presets,
            "metric": self.get_metric(),
            "num_folds": self.num_folds,
        }

    @classmethod
    def for_automl(
        cls,
        target_column: str,
        problem_type: ProblemType,
        time_limit: int = 300,
        presets: str = "medium_quality",
    ) -> "TrainingConfig":
        """Factory method for AutoML configuration"""
        return cls(
            target_column=target_column,
            problem_type=problem_type,
            algorithms=None,
            time_limit=time_limit,
            presets=presets,
        )

    @classmethod
    def for_specific_algorithms(
        cls,
        target_column: str,
        problem_type: ProblemType,
        algorithms: List[str],
        time_limit: int = 300,
    ) -> "TrainingConfig":
        """Factory method for specific algorithm training"""
        return cls(
            target_column=target_column,
            problem_type=problem_type,
            algorithms=algorithms,
            time_limit=time_limit,
            presets="medium_quality",
        )

    @classmethod
    def for_comparison(
        cls,
        target_column: str,
        problem_type: ProblemType,
        algorithms: List[str],
        time_limit: int = 300,
    ) -> "TrainingConfig":
        """Factory method for algorithm comparison"""
        return cls(
            target_column=target_column,
            problem_type=problem_type,
            algorithms=algorithms,
            time_limit=time_limit,
            presets="medium_quality",
        )

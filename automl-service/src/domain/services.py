"""
Domain Services - Business logic that doesn't belong to a single entity
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Callable, Optional
import pandas as pd

from .models import TrainingConfig, LeaderboardEntry


class MLEngineService(ABC):
    """
    Domain Service Interface for ML Engine
    
    Defines the contract for ML training operations.
    Implementation will use AutoGluon.
    """

    @abstractmethod
    async def train(
        self,
        data: pd.DataFrame,
        config: TrainingConfig,
        model_save_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float, List[LeaderboardEntry], Dict[str, float]]:
        """
        Train a model using the provided configuration.
        
        Args:
            data: Training DataFrame
            config: Training configuration
            model_save_path: Path to save the trained model
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (best_model_name, best_score, leaderboard, feature_importance)
        """
        pass

    @abstractmethod
    async def predict(
        self,
        model_path: str,
        data: pd.DataFrame,
    ) -> List[Any]:
        """
        Make predictions using a trained model.
        
        Args:
            model_path: Path to the saved model
            data: DataFrame for prediction
            
        Returns:
            List of predictions
        """
        pass

    @abstractmethod
    async def predict_proba(
        self,
        model_path: str,
        data: pd.DataFrame,
    ) -> List[List[float]]:
        """
        Get prediction probabilities.
        
        Args:
            model_path: Path to the saved model
            data: DataFrame for prediction
            
        Returns:
            List of probability arrays
        """
        pass


class FileStorageService(ABC):
    """
    Domain Service Interface for File Storage
    
    Defines the contract for file operations.
    Implementation will use MinIO.
    """

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if file exists at the given path"""
        pass

    @abstractmethod
    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from storage to local path"""
        pass

    @abstractmethod
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata (size, modified time, etc.)"""
        pass

    @abstractmethod
    async def read_csv(self, path: str) -> pd.DataFrame:
        """Read CSV file from storage into DataFrame"""
        pass

    @abstractmethod
    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        """
        Validate CSV file format.
        
        Returns:
            Tuple of (is_valid, columns, row_count)
        """
        pass

"""
Repository Interfaces - Domain Layer

Abstract interfaces that define how domain objects are persisted.
Actual implementations are in the Infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from .models import StatsJob, StatsJobId


class StatsJobRepository(ABC):
    """Repository interface for StatsJob aggregate"""

    @abstractmethod
    async def save(self, job: StatsJob) -> None:
        """Save a job"""
        pass

    @abstractmethod
    async def get_by_id(self, job_id: StatsJobId) -> Optional[StatsJob]:
        """Get job by ID"""
        pass

    @abstractmethod
    async def find_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[StatsJob]:
        """Find all jobs for a user/session"""
        pass

    @abstractmethod
    async def find_pending(self) -> List[StatsJob]:
        """Find all pending jobs"""
        pass

    @abstractmethod
    async def update(self, job: StatsJob) -> None:
        """Update a job"""
        pass

    @abstractmethod
    async def delete(self, job_id: StatsJobId) -> bool:
        """Delete a job"""
        pass

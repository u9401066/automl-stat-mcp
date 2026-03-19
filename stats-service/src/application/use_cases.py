"""
Use Cases - Application Layer Business Logic
"""

from typing import List, Optional

from ..domain.models import (
    StatsJob,
    StatsJobId,
    StatsJobType,
)
from ..domain.repositories import StatsJobRepository
from .dto import (
    StatsJobResponse,
    SubmitAutoAnalyzeRequest,
    SubmitEDARequest,
    SubmitTableOneRequest,
)


class DatasetNotFoundError(Exception):
    """Dataset not found in Redis"""

    pass


class SubmitAutoAnalyzeUseCase:
    """Use case for submitting auto-analyze job"""

    def __init__(
        self,
        job_repo: StatsJobRepository,
        dataset_store,  # redis_dataset_store
        job_queue,  # redis job queue
    ):
        self.job_repo = job_repo
        self.dataset_store = dataset_store
        self.job_queue = job_queue

    async def execute(self, request: SubmitAutoAnalyzeRequest) -> StatsJobResponse:
        # 1. Get dataset metadata from shared Redis store
        dataset_info = self.dataset_store.get_dataset(request.dataset_id)
        if not dataset_info:
            raise DatasetNotFoundError(
                f"Dataset {request.dataset_id} not found. Please register it first using AutoML service."
            )

        # 2. Create job entity
        job = StatsJob(
            id=StatsJobId.generate(),
            job_type=StatsJobType.AUTO_ANALYZE,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            minio_path=dataset_info.get("minio_path"),
            session_id=request.session_id,
            params={
                "target_column": request.target_column,
            },
        )

        # 3. Save to repository
        await self.job_repo.save(job)

        # 4. Enqueue job for worker
        await self.job_queue.enqueue_job(job)

        # 5. Return response
        return StatsJobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            message="Auto-analysis job submitted. Use /jobs/{job_id} to check status.",
        )


class SubmitEDAUseCase:
    """Use case for submitting EDA job"""

    def __init__(
        self,
        job_repo: StatsJobRepository,
        dataset_store,
        job_queue,
    ):
        self.job_repo = job_repo
        self.dataset_store = dataset_store
        self.job_queue = job_queue

    async def execute(self, request: SubmitEDARequest) -> StatsJobResponse:
        # 1. Get dataset metadata
        dataset_info = self.dataset_store.get_dataset(request.dataset_id)
        if not dataset_info:
            raise DatasetNotFoundError(
                f"Dataset {request.dataset_id} not found. Please register it first using AutoML service."
            )

        # 2. Create job entity
        job = StatsJob(
            id=StatsJobId.generate(),
            job_type=StatsJobType.EDA,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            minio_path=dataset_info.get("minio_path"),
            session_id=request.session_id,
            params={
                "title": request.title,
                "minimal": request.minimal,
            },
        )

        # 3. Save and enqueue
        await self.job_repo.save(job)
        await self.job_queue.enqueue_job(job)

        return StatsJobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            message="EDA job submitted. Use /jobs/{job_id} to check status.",
        )


class SubmitTableOneUseCase:
    """Use case for submitting TableOne job"""

    def __init__(
        self,
        job_repo: StatsJobRepository,
        dataset_store,
        job_queue,
    ):
        self.job_repo = job_repo
        self.dataset_store = dataset_store
        self.job_queue = job_queue

    async def execute(self, request: SubmitTableOneRequest) -> StatsJobResponse:
        # 1. Get dataset metadata
        dataset_info = self.dataset_store.get_dataset(request.dataset_id)
        if not dataset_info:
            raise DatasetNotFoundError(
                f"Dataset {request.dataset_id} not found. Please register it first using AutoML service."
            )

        # 2. Create job entity
        job = StatsJob(
            id=StatsJobId.generate(),
            job_type=StatsJobType.TABLEONE,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            minio_path=dataset_info.get("minio_path"),
            session_id=request.session_id,
            params={
                "columns": request.columns,
                "categorical": request.categorical,
                "continuous": request.continuous,
                "groupby": request.groupby,
                "nonnormal": request.nonnormal,
                "pval": request.pval,
            },
        )

        # 3. Save and enqueue
        await self.job_repo.save(job)
        await self.job_queue.enqueue_job(job)

        return StatsJobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            message="TableOne job submitted. Use /jobs/{job_id} to check status.",
        )


class GetJobStatusUseCase:
    """Use case for getting job status"""

    def __init__(self, job_repo: StatsJobRepository):
        self.job_repo = job_repo

    async def execute(self, job_id: str) -> Optional[StatsJobResponse]:
        try:
            job_id_obj = StatsJobId.from_string(job_id)
        except ValueError:
            return None

        job = await self.job_repo.get_by_id(job_id_obj)
        if not job:
            return None

        return StatsJobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            message=job.message,
            result_path=job.result_path,
            error=job.error,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )


class GetJobResultUseCase:
    """Use case for getting job result"""

    def __init__(self, job_repo: StatsJobRepository):
        self.job_repo = job_repo

    async def execute(self, job_id: str) -> Optional[StatsJobResponse]:
        try:
            job_id_obj = StatsJobId.from_string(job_id)
        except ValueError:
            return None

        job = await self.job_repo.get_by_id(job_id_obj)
        if not job:
            return None

        return StatsJobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            message=job.message,
            result_path=job.result_path,
            result=job.result,
            error=job.error,
            created_at=job.created_at.isoformat() if job.created_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )


class ListJobsUseCase:
    """Use case for listing jobs"""

    def __init__(self, job_repo: StatsJobRepository):
        self.job_repo = job_repo

    async def execute(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[StatsJobResponse]:
        jobs = await self.job_repo.find_by_user(
            user_id=user_id,
            session_id=session_id,
            job_type=job_type,
            limit=limit,
        )

        return [
            StatsJobResponse(
                job_id=str(job.id),
                job_type=job.job_type.value,
                status=job.status.value,
                progress=job.progress,
                message=job.message,
                result_path=job.result_path,
                error=job.error,
                created_at=job.created_at.isoformat() if job.created_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
            )
            for job in jobs
        ]

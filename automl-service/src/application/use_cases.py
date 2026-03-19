"""
Use Cases - Application Layer Business Logic
"""

from typing import List, Optional

from ..domain.models import (
    Dataset,
    DatasetId,
    Job,
    JobId,
    JobType,
    ProblemType,
    TrainingConfig,
)
from ..domain.repositories import DatasetRepository, JobRepository
from ..domain.services import FileStorageService
from .dto import (
    AutoMLTrainRequest,
    CompareModelsRequest,
    DatasetResponse,
    JobResponse,
    RegisterDatasetRequest,
    SpecificTrainRequest,
)


class RegisterDatasetUseCase:
    """Use case for registering a dataset from MinIO"""

    def __init__(
        self,
        dataset_repo: DatasetRepository,
        file_storage: FileStorageService,
    ):
        self.dataset_repo = dataset_repo
        self.file_storage = file_storage

    async def execute(self, request: RegisterDatasetRequest) -> DatasetResponse:
        # 1. Validate file exists in MinIO
        if not await self.file_storage.file_exists(request.minio_path):
            raise ValueError(f"File not found: {request.minio_path}")

        # 2. Validate CSV and get metadata
        is_valid, columns, row_count = await self.file_storage.validate_csv(request.minio_path)
        if not is_valid:
            raise ValueError(f"Invalid CSV file: {request.minio_path}")

        # 3. Get file info
        file_info = await self.file_storage.get_file_info(request.minio_path)

        # 4. Create dataset entity
        dataset = Dataset(
            id=DatasetId.generate(),
            name=request.name,
            minio_path=request.minio_path,
            user_id=request.user_id,
            session_id=request.session_id,
            description=request.description,
            columns=columns,
            row_count=row_count,
            file_size_bytes=file_info.get("size", 0),
        )

        # 5. Save to repository
        await self.dataset_repo.save(dataset)

        # 6. Return response
        return DatasetResponse(
            dataset_id=str(dataset.id),
            name=dataset.name,
            minio_path=dataset.minio_path,
            columns=dataset.columns,
            row_count=dataset.row_count,
            file_size_bytes=dataset.file_size_bytes,
            created_at=dataset.created_at.isoformat(),
            description=dataset.description,
        )


class ListDatasetsUseCase:
    """Use case for listing user's datasets"""

    def __init__(self, dataset_repo: DatasetRepository):
        self.dataset_repo = dataset_repo

    async def execute(self, user_id: str, session_id: Optional[str] = None) -> List[DatasetResponse]:
        datasets = await self.dataset_repo.find_by_user(user_id, session_id)

        return [
            DatasetResponse(
                dataset_id=str(ds.id),
                name=ds.name,
                minio_path=ds.minio_path,
                columns=ds.columns,
                row_count=ds.row_count,
                file_size_bytes=ds.file_size_bytes,
                created_at=ds.created_at.isoformat(),
                description=ds.description,
            )
            for ds in datasets
        ]


class SubmitAutoMLJobUseCase:
    """Use case for submitting an AutoML training job"""

    def __init__(
        self,
        dataset_repo: DatasetRepository,
        job_repo: JobRepository,
    ):
        self.dataset_repo = dataset_repo
        self.job_repo = job_repo

    async def execute(self, request: AutoMLTrainRequest) -> JobResponse:
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await self.dataset_repo.get_by_id(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")

        if not dataset.belongs_to(request.user_id, request.session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column exists
        if not dataset.has_column(request.target_column):
            raise ValueError(f"Target column '{request.target_column}' not found in dataset")

        # 3. Create training config
        config = TrainingConfig.for_automl(
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            time_limit=request.time_limit,
            presets=request.presets,
        )

        # 4. Create job
        job = Job(
            id=JobId.generate(),
            job_type=JobType.AUTOML,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            session_id=request.session_id,
            config=config.to_dict(),
        )

        # 5. Save job
        await self.job_repo.save(job)

        # 6. Return response (job will be picked up by worker)
        return JobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            status_message=job.status_message,
            created_at=job.created_at.isoformat(),
        )


class SubmitSpecificTrainJobUseCase:
    """Use case for training with specific algorithms"""

    def __init__(
        self,
        dataset_repo: DatasetRepository,
        job_repo: JobRepository,
    ):
        self.dataset_repo = dataset_repo
        self.job_repo = job_repo

    async def execute(self, request: SpecificTrainRequest) -> JobResponse:
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await self.dataset_repo.get_by_id(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")

        if not dataset.belongs_to(request.user_id, request.session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column
        if not dataset.has_column(request.target_column):
            raise ValueError(f"Target column '{request.target_column}' not found in dataset")

        # 3. Create training config
        config = TrainingConfig.for_specific_algorithms(
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            algorithms=request.algorithms,
            time_limit=request.time_limit,
        )

        # 4. Create job
        job = Job(
            id=JobId.generate(),
            job_type=JobType.SPECIFIC,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            session_id=request.session_id,
            config=config.to_dict(),
        )

        # 5. Save job
        await self.job_repo.save(job)

        return JobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            status_message=job.status_message,
            created_at=job.created_at.isoformat(),
        )


class SubmitCompareJobUseCase:
    """Use case for comparing multiple algorithms"""

    def __init__(
        self,
        dataset_repo: DatasetRepository,
        job_repo: JobRepository,
    ):
        self.dataset_repo = dataset_repo
        self.job_repo = job_repo

    async def execute(self, request: CompareModelsRequest) -> JobResponse:
        # 1. Validate dataset exists
        dataset_id = DatasetId.from_string(request.dataset_id)
        dataset = await self.dataset_repo.get_by_id(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset not found: {request.dataset_id}")

        if not dataset.belongs_to(request.user_id, request.session_id):
            raise PermissionError("Access denied to dataset")

        # 2. Validate target column
        if not dataset.has_column(request.target_column):
            raise ValueError(f"Target column '{request.target_column}' not found in dataset")

        # 3. Validate at least 2 algorithms for comparison
        if len(request.algorithms) < 2:
            raise ValueError("At least 2 algorithms required for comparison")

        # 4. Create training config
        config = TrainingConfig.for_comparison(
            target_column=request.target_column,
            problem_type=ProblemType(request.problem_type),
            algorithms=request.algorithms,
            time_limit=request.time_limit,
        )

        # 5. Create job
        job = Job(
            id=JobId.generate(),
            job_type=JobType.COMPARE,
            user_id=request.user_id,
            dataset_id=request.dataset_id,
            session_id=request.session_id,
            config=config.to_dict(),
        )

        # 6. Save job
        await self.job_repo.save(job)

        return JobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            status_message=job.status_message,
            created_at=job.created_at.isoformat(),
        )


class GetJobStatusUseCase:
    """Use case for getting job status"""

    def __init__(self, job_repo: JobRepository):
        self.job_repo = job_repo

    async def execute(self, job_id: str, user_id: str) -> JobResponse:
        job_id_obj = JobId.from_string(job_id)
        job = await self.job_repo.get_by_id(job_id_obj)

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if not job.belongs_to(user_id):
            raise PermissionError("Access denied to job")

        return JobResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress,
            status_message=job.status_message,
            model_id=job.model_id,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )

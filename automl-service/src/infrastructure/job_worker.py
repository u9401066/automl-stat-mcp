"""
Job Worker - Background worker for processing training jobs
"""
import asyncio
from typing import Dict, Any, Set
from datetime import datetime
import logging

from ..domain.models import (
    Job, JobId, JobStatus,
    MLModel, ModelId, 
    DatasetId,
    TrainingConfig, ProblemType,
)
from ..domain.repositories import JobRepository, DatasetRepository, ModelRepository
from ..domain.services import MLEngineService, FileStorageService
from ..config import MODELS_DIR

logger = logging.getLogger(__name__)


class JobWorker:
    """
    Background worker that processes pending training jobs.
    
    Uses WebSocket to notify clients of progress.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        dataset_repo: DatasetRepository,
        model_repo: ModelRepository,
        ml_engine: MLEngineService,
        file_storage: FileStorageService,
    ):
        self.job_repo = job_repo
        self.dataset_repo = dataset_repo
        self.model_repo = model_repo
        self.ml_engine = ml_engine
        self.file_storage = file_storage
        
        self._running = False
        self._active_jobs: Set[str] = set()
        self._websocket_callbacks: Dict[str, Any] = {}

    def register_websocket(self, job_id: str, callback):
        """Register a WebSocket callback for job updates"""
        self._websocket_callbacks[job_id] = callback

    def unregister_websocket(self, job_id: str):
        """Unregister a WebSocket callback"""
        self._websocket_callbacks.pop(job_id, None)

    async def _notify_progress(self, job: Job):
        """Send progress update via WebSocket"""
        callback = self._websocket_callbacks.get(str(job.id))
        if callback:
            try:
                await callback(job.to_dict())
            except Exception as e:
                logger.warning(f"Failed to send WebSocket update: {e}")

    async def _process_job(self, job: Job):
        """Process a single training job"""
        job_id = str(job.id)
        
        if job_id in self._active_jobs:
            return
        
        self._active_jobs.add(job_id)
        
        try:
            # Mark as running
            job.start()
            await self.job_repo.update(job)
            await self._notify_progress(job)
            
            # Load dataset
            dataset_id = DatasetId.from_string(job.dataset_id)
            dataset = await self.dataset_repo.get_by_id(dataset_id)
            
            if not dataset:
                raise ValueError(f"Dataset not found: {job.dataset_id}")
            
            # Read data from MinIO
            job.update_progress(0.1, "Loading dataset...")
            await self.job_repo.update(job)
            await self._notify_progress(job)
            
            data = await self.file_storage.read_csv(dataset.minio_path)
            
            # Create training config
            config = TrainingConfig(
                target_column=job.config["target_column"],
                problem_type=ProblemType(job.config["problem_type"]),
                algorithms=job.config.get("algorithms"),
                time_limit=job.config.get("time_limit", 300),
                presets=job.config.get("presets", "medium_quality"),
            )
            
            # Model save path
            model_id = ModelId.generate()
            model_path = str(MODELS_DIR / str(model_id))
            
            # Progress callback
            async def progress_callback(progress: float, message: str):
                job.update_progress(0.1 + progress * 0.8, message)
                await self.job_repo.update(job)
                await self._notify_progress(job)
            
            # Train model
            job.update_progress(0.15, "Training started...")
            await self.job_repo.update(job)
            await self._notify_progress(job)
            
            best_model_name, best_score, leaderboard, feature_importance = \
                await self.ml_engine.train(
                    data=data,
                    config=config,
                    model_save_path=model_path,
                    progress_callback=progress_callback,
                )
            
            # Create model entity
            model = MLModel(
                id=model_id,
                name=f"model_{job.job_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                user_id=job.user_id,
                dataset_id=job.dataset_id,
                problem_type=config.problem_type.value,
                target_column=config.target_column,
                model_path=model_path,
                best_model_name=best_model_name,
                best_score=best_score,
                metric=config.get_metric(),
                leaderboard=leaderboard,
                feature_importance=feature_importance,
                algorithms_used=config.algorithms or ["AutoML"],
                time_limit=config.time_limit,
                presets=config.presets,
                session_id=job.session_id,
            )
            
            # Save model
            await self.model_repo.save(model)
            
            # Complete job
            result = {
                "best_model_name": best_model_name,
                "best_score": best_score,
                "metric": config.get_metric(),
                "leaderboard": [e.to_dict() for e in leaderboard],
            }
            job.complete(str(model_id), result)
            await self.job_repo.update(job)
            await self._notify_progress(job)
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.fail(str(e))
            await self.job_repo.update(job)
            await self._notify_progress(job)
        
        finally:
            self._active_jobs.discard(job_id)

    async def run(self):
        """Main worker loop"""
        self._running = True
        logger.info("Job worker started")
        
        while self._running:
            try:
                # Find pending jobs
                pending_jobs = await self.job_repo.find_pending()
                
                # Process each pending job
                for job in pending_jobs:
                    if str(job.id) not in self._active_jobs:
                        # Start job processing in background
                        asyncio.create_task(self._process_job(job))
                
                # Wait before checking again
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        """Stop the worker"""
        self._running = False
        logger.info("Job worker stopped")

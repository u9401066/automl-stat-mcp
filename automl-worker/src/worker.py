"""
AutoGluon Worker - Job Consumer

Pulls jobs from Redis queue, runs AutoGluon training, saves results to MinIO.

Supports:
- GPU acceleration (auto-detected)
- CPU fallback when GPU unavailable
- Multiple worker instances for scaling

This runs in the official AutoGluon container - no need to maintain AutoGluon installation.
"""
import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import redis
from minio import Minio

# AutoGluon imports (available from base image)
from autogluon.tabular import TabularPredictor

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def detect_gpu() -> Tuple[bool, str]:
    """
    Detect if GPU is available for training.
    
    Returns:
        (gpu_available, device_info)
    """
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            return True, f"GPU: {gpu_name} (x{gpu_count})"
        else:
            return False, "CPU only (CUDA not available)"
    except ImportError:
        return False, "CPU only (PyTorch not installed)"
    except Exception as e:
        return False, f"CPU only (GPU detection failed: {e})"


class AutoGluonWorker:
    """
    Worker that consumes training jobs from Redis queue.
    
    Features:
    - Auto GPU/CPU detection
    - Horizontal scaling via multiple workers
    - MinIO model storage
    
    Flow:
    1. Pop job from Redis queue
    2. Download dataset from MinIO
    3. Run AutoGluon training (GPU if available)
    4. Upload trained model to MinIO
    5. Update job status in Redis
    """
    
    def __init__(self):
        # Detect GPU availability
        self.gpu_available, self.device_info = detect_gpu()
        
        # Worker identity (for scaling)
        self.worker_id = os.environ.get("WORKER_ID", os.environ.get("HOSTNAME", "worker-1"))
        self.worker_type = os.environ.get("WORKER_TYPE", "auto")  # cpu, gpu, or auto
        
        # Redis connection
        self.redis = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True,
        )
        
        # MinIO connection
        self.minio = Minio(
            endpoint=os.environ.get("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
        )
        
        # Buckets
        self.dataset_bucket = os.environ.get("MINIO_DATASET_BUCKET", "automl-datasets")
        self.model_bucket = os.environ.get("MINIO_MODEL_BUCKET", "automl-models")
        
        # Temp directory
        self.temp_dir = Path(os.environ.get("WORKER_TEMP_DIR", "/tmp/autogluon-work"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Queue names
        self.job_queue = "automl:jobs:pending"
        self.job_prefix = "automl:job:"
        
        # Redis TTL settings (seconds)
        self.job_ttl = int(os.environ.get("REDIS_JOB_TTL", str(24 * 60 * 60)))  # 24 hours
        self.worker_ttl = int(os.environ.get("REDIS_WORKER_TTL", str(60 * 60)))  # 1 hour
        
        logger.info(f"AutoGluon Worker initialized: {self.worker_id}")
        logger.info(f"Device: {self.device_info}")
        logger.info(f"Worker type: {self.worker_type}")

    def run(self):
        """Main worker loop"""
        logger.info(f"Starting worker loop... ({self.worker_id})")
        
        # Register worker in Redis for monitoring
        self._register_worker()
        
        while True:
            try:
                # Blocking pop from queue (wait up to 5 seconds)
                result = self.redis.brpop(self.job_queue, timeout=5)
                
                if result:
                    _, job_id = result
                    self._process_job(job_id)
                else:
                    # Heartbeat when idle
                    self._update_worker_heartbeat()
                    
            except KeyboardInterrupt:
                logger.info("Worker shutting down...")
                self._unregister_worker()
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                asyncio.sleep(1)
    
    def _register_worker(self):
        """Register this worker in Redis for monitoring (with TTL)"""
        worker_info = {
            "id": self.worker_id,
            "type": self.worker_type,
            "device": self.device_info,
            "gpu_available": str(self.gpu_available),
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }
        worker_key = f"automl:workers:{self.worker_id}"
        self.redis.hset(worker_key, mapping=worker_info)
        self.redis.expire(worker_key, self.worker_ttl)  # Auto-expire if worker dies
        self.redis.sadd("automl:workers:active", self.worker_id)
        logger.info(f"Worker registered: {self.worker_id}")
    
    def _unregister_worker(self):
        """Unregister this worker from Redis"""
        self.redis.srem("automl:workers:active", self.worker_id)
        self.redis.hset(f"automl:workers:{self.worker_id}", "status", "stopped")
        logger.info(f"Worker unregistered: {self.worker_id}")
    
    def _update_worker_heartbeat(self):
        """Update worker heartbeat in Redis (refresh TTL)"""
        worker_key = f"automl:workers:{self.worker_id}"
        self.redis.hset(worker_key, "last_heartbeat", datetime.utcnow().isoformat())
        self.redis.expire(worker_key, self.worker_ttl)  # Refresh TTL on heartbeat

    def _process_job(self, job_id: str):
        """Process a single training job"""
        logger.info(f"Processing job: {job_id} (worker: {self.worker_id})")
        
        work_dir = None
        try:
            # Get job details from Redis
            job_data = self.redis.hgetall(f"{self.job_prefix}{job_id}")
            if not job_data:
                logger.error(f"Job not found: {job_id}")
                return
            
            # Parse job config
            config = json.loads(job_data.get("config", "{}"))
            
            # Update status to running
            self._update_job_status(job_id, "running", progress=0.0)
            
            # Create temp work directory
            work_dir = self.temp_dir / job_id
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # Download dataset from MinIO
            dataset_path = self._download_dataset(config["dataset_minio_path"], work_dir)
            
            self._update_job_status(job_id, "running", progress=0.1, message="Dataset loaded")
            
            # Run AutoGluon training
            model_path = self._train_model(job_id, dataset_path, config, work_dir)
            
            self._update_job_status(job_id, "running", progress=0.9, message="Uploading model")
            
            # Upload model to MinIO
            model_minio_path = self._upload_model(job_id, model_path)
            
            # Get leaderboard
            predictor = TabularPredictor.load(str(model_path))
            leaderboard = predictor.leaderboard().to_dict(orient="records")
            
            # Mark job as completed
            self._update_job_status(
                job_id, 
                "completed", 
                progress=1.0,
                message="Training completed",
                result={
                    "model_minio_path": model_minio_path,
                    "leaderboard": leaderboard,
                    "best_model": predictor.model_best,  # Property, not method
                }
            )
            
            logger.info(f"Job completed: {job_id}")
            
        except Exception as e:
            logger.error(f"Job failed: {job_id} - {e}")
            self._update_job_status(
                job_id, 
                "failed", 
                progress=0.0,
                message=str(e),
            )
        finally:
            # Cleanup temp directory
            if work_dir and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    def _download_dataset(self, minio_path: str, work_dir: Path) -> Path:
        """Download dataset from MinIO to temp directory"""
        # Remove s3:// or minio:// prefix
        if minio_path.startswith("s3://"):
            minio_path = minio_path[5:]
        elif minio_path.startswith("minio://"):
            minio_path = minio_path[8:]
        
        # Parse path: bucket/path/to/file.csv
        parts = minio_path.split("/", 1)
        bucket = parts[0] if len(parts) > 1 else self.dataset_bucket
        object_name = parts[1] if len(parts) > 1 else parts[0]
        
        local_path = work_dir / "dataset.csv"
        self.minio.fget_object(bucket, object_name, str(local_path))
        
        logger.info(f"Downloaded dataset: {bucket}/{object_name} -> {local_path}")
        return local_path

    def _train_model(
        self, 
        job_id: str, 
        dataset_path: Path, 
        config: Dict[str, Any],
        work_dir: Path,
    ) -> Path:
        """Run AutoGluon training with GPU/CPU auto-detection"""
        import pandas as pd
        
        # Load data
        df = pd.read_csv(dataset_path)
        
        # Model output path
        model_path = work_dir / "model"
        
        # Build predictor config
        predictor_args = {
            "label": config["target_column"],
            "path": str(model_path),
            "problem_type": config.get("problem_type"),
            "eval_metric": config.get("metric"),
        }
        
        # Build fit config
        fit_args = {
            "time_limit": config.get("time_limit", 300),
            "presets": config.get("presets", "medium_quality"),
        }
        
        # Handle specific algorithms
        if config.get("algorithms"):
            fit_args["hyperparameters"] = {
                algo: {} for algo in config["algorithms"]
            }
        
        # GPU/CPU configuration for neural networks
        if self.gpu_available:
            # Use GPU for neural network models
            fit_args["ag_args_fit"] = {"num_gpus": 1}
            logger.info("Training with GPU acceleration")
        else:
            # Force CPU for neural networks
            fit_args["ag_args_fit"] = {"num_gpus": 0}
            logger.info("Training with CPU")
        
        # Create and train predictor
        logger.info(f"Starting AutoGluon training: {predictor_args}")
        logger.info(f"Fit args: {fit_args}")
        predictor = TabularPredictor(**predictor_args)
        
        # Progress callback (simplified)
        self._update_job_status(
            job_id, 
            "running", 
            progress=0.2, 
            message=f"Training started ({self.device_info})"
        )
        
        predictor.fit(df, **fit_args)
        
        self._update_job_status(job_id, "running", progress=0.8, message="Training completed")
        
        return model_path

    def _upload_model(self, job_id: str, model_path: Path) -> str:
        """Upload trained model to MinIO"""
        import tarfile
        
        # Create tar.gz of model directory
        tar_path = model_path.parent / f"{job_id}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(model_path, arcname="model")
        
        # Upload to MinIO
        object_name = f"models/{job_id}/model.tar.gz"
        self.minio.fput_object(self.model_bucket, object_name, str(tar_path))
        
        minio_path = f"{self.model_bucket}/{object_name}"
        logger.info(f"Uploaded model: {minio_path}")
        
        return minio_path

    def _update_job_status(
        self, 
        job_id: str, 
        status: str, 
        progress: float = 0.0,
        message: str = "",
        result: Optional[Dict] = None,
    ):
        """Update job status in Redis"""
        update = {
            "status": status,
            "progress": progress,
            "status_message": message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if result:
            update["result"] = json.dumps(result)
        
        if status == "completed":
            update["completed_at"] = datetime.utcnow().isoformat()
        
        job_key = f"{self.job_prefix}{job_id}"
        self.redis.hset(job_key, mapping=update)
        self.redis.expire(job_key, self.job_ttl)  # Job data expires after 24h
        
        # Publish status update for WebSocket subscribers
        self.redis.publish(f"automl:job:{job_id}:status", json.dumps(update))


def main():
    """Entry point"""
    worker = AutoGluonWorker()
    worker.run()


if __name__ == "__main__":
    main()

"""
Redis Job Queue Client

Handles job submission to Redis queue for AutoGluon workers.
Uses shared RedisManager for connection pooling.
"""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis

# Import shared RedisManager
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from shared.infrastructure.redis_manager import get_sync_client

from src.domain.models.job import Job, JobId, JobStatus, JobType
from src.domain.models.training_config import TrainingConfig

logger = logging.getLogger(__name__)


class RedisJobQueue:
    """
    Redis-based job queue using shared RedisManager.

    Architecture:
    - Jobs are pushed to a Redis list (queue)
    - Workers pop jobs and process them
    - Job status is stored in Redis hashes
    - Status updates published via Redis pub/sub
    """

    def __init__(self):
        # Lazy initialization - get client from RedisManager on first use
        self._redis = None

        # Key prefixes
        self._queue_key = "automl:jobs:pending"
        self._job_prefix = "automl:job:"
    
    def _get_client(self) -> redis.Redis:
        """Get Redis client from shared connection pool."""
        if self._redis is None:
            self._redis = get_sync_client()
        return self._redis

    def submit_job(
        self,
        job_type: JobType,
        user_id: str,
        session_id: Optional[str],
        config: TrainingConfig,
        dataset_minio_path: str,
    ) -> Job:
        """
        Submit a new training job to the queue.

        Returns immediately with a pending Job.
        The actual training happens in the worker container.
        """
        job_id = str(uuid4())
        now = datetime.utcnow()

        # Create job record
        job = Job(
            id=JobId.from_string(job_id),
            job_type=job_type,
            user_id=user_id,
            dataset_id=config.dataset_id,
            session_id=session_id,
            status=JobStatus.PENDING,
            config=config.__dict__ if hasattr(config, '__dict__') else {},
            created_at=now,
        )

        # Prepare job data for Redis
        job_data = {
            "id": job_id,
            "job_type": job_type.value,
            "user_id": user_id,
            "session_id": session_id or "",
            "status": JobStatus.PENDING.value,
            "progress": 0.0,
            "status_message": "Queued for processing",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "config": json.dumps({
                "dataset_id": config.dataset_id,
                "dataset_minio_path": dataset_minio_path,
                "target_column": config.target_column,
                "problem_type": config.problem_type.value,
                "time_limit": config.time_limit,
                "presets": config.presets,
                "metric": config.metric,
                "algorithms": config.algorithms,
            }),
        }

        # Store job in Redis hash
        redis_client = self._get_client()
        redis_client.hset(f"{self._job_prefix}{job_id}", mapping=job_data)

        # Add to queue for workers to pick up
        redis_client.lpush(self._queue_key, job_id)

        logger.info(f"Submitted job {job_id} to Redis queue")
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details from Redis"""
        redis_client = self._get_client()
        data = redis_client.hgetall(f"{self._job_prefix}{job_id}")
        if not data:
            return None

        # Parse result if present
        result = None
        if data.get("result"):
            result = json.loads(data["result"])

        return {
            "id": data["id"],
            "job_type": data["job_type"],
            "user_id": data["user_id"],
            "session_id": data.get("session_id") or None,
            "status": data["status"],
            "progress": float(data.get("progress", 0)),
            "status_message": data.get("status_message", ""),
            "model_id": result.get("model_id") if result else None,
            "result": result,
            "error_message": data.get("error_message"),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "completed_at": data.get("completed_at"),
        }

    def list_jobs(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List jobs for a user"""
        # Scan for all job keys
        redis_client = self._get_client()
        jobs = []
        cursor = 0

        while True:
            cursor, keys = redis_client.scan(
                cursor=cursor,
                match=f"{self._job_prefix}*",
                count=100
            )

            for key in keys:
                data = redis_client.hgetall(key)
                if data.get("user_id") == user_id:
                    if session_id is None or data.get("session_id") == session_id:
                        jobs.append(self.get_job(data["id"]))

            if cursor == 0:
                break

        # Sort by created_at descending
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        return jobs

    def cancel_job(self, job_id: str, user_id: str) -> bool:
        """
        Cancel a pending job.

        Cannot cancel running or completed jobs.
        """
        redis_client = self._get_client()
        data = redis_client.hgetall(f"{self._job_prefix}{job_id}")

        if not data:
            return False

        if data["user_id"] != user_id:
            return False

        if data["status"] != JobStatus.PENDING.value:
            return False

        # Remove from queue
        redis_client.lrem(self._queue_key, 0, job_id)

        # Update status
        redis_client.hset(
            f"{self._job_prefix}{job_id}",
            mapping={
                "status": JobStatus.CANCELLED.value,
                "status_message": "Cancelled by user",
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

        logger.info(f"Cancelled job {job_id}")
        return True

    def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a job record"""
        redis_client = self._get_client()
        data = redis_client.hgetall(f"{self._job_prefix}{job_id}")

        if not data:
            return False

        if data["user_id"] != user_id:
            return False

        # Remove from queue if pending
        redis_client.lrem(self._queue_key, 0, job_id)

        # Delete job record
        redis_client.delete(f"{self._job_prefix}{job_id}")

        logger.info(f"Deleted job {job_id}")
        return True


# Singleton instance
_job_queue: Optional[RedisJobQueue] = None


def get_job_queue() -> RedisJobQueue:
    """Get or create job queue instance"""
    global _job_queue
    if _job_queue is None:
        _job_queue = RedisJobQueue()
    return _job_queue

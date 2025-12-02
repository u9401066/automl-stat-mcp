"""
Redis Job Queue Client

Handles job submission to Redis queue for AutoGluon workers.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis

from src.domain.models.job import Job, JobStatus, JobType
from src.domain.models.training_config import TrainingConfig


class RedisJobQueue:
    """
    Redis-based job queue for distributing training jobs to workers.
    
    Architecture:
    - Jobs are pushed to a Redis list (queue)
    - Workers pop jobs and process them
    - Job status is stored in Redis hashes
    - Status updates published via Redis pub/sub
    """
    
    def __init__(self):
        self._redis = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True,
        )
        
        # Key prefixes
        self._queue_key = "automl:jobs:pending"
        self._job_prefix = "automl:job:"
    
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
            id=job_id,
            job_type=job_type,
            user_id=user_id,
            session_id=session_id,
            status=JobStatus.PENDING,
            config=config,
            created_at=now,
            updated_at=now,
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
        self._redis.hset(f"{self._job_prefix}{job_id}", mapping=job_data)
        
        # Add to queue for workers to pick up
        self._redis.lpush(self._queue_key, job_id)
        
        return job
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details from Redis"""
        data = self._redis.hgetall(f"{self._job_prefix}{job_id}")
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
        jobs = []
        cursor = 0
        
        while True:
            cursor, keys = self._redis.scan(
                cursor=cursor, 
                match=f"{self._job_prefix}*",
                count=100
            )
            
            for key in keys:
                data = self._redis.hgetall(key)
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
        data = self._redis.hgetall(f"{self._job_prefix}{job_id}")
        
        if not data:
            return False
        
        if data["user_id"] != user_id:
            return False
        
        if data["status"] != JobStatus.PENDING.value:
            return False
        
        # Remove from queue
        self._redis.lrem(self._queue_key, 0, job_id)
        
        # Update status
        self._redis.hset(
            f"{self._job_prefix}{job_id}",
            mapping={
                "status": JobStatus.CANCELLED.value,
                "status_message": "Cancelled by user",
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        
        return True
    
    def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a job record"""
        data = self._redis.hgetall(f"{self._job_prefix}{job_id}")
        
        if not data:
            return False
        
        if data["user_id"] != user_id:
            return False
        
        # Remove from queue if pending
        self._redis.lrem(self._queue_key, 0, job_id)
        
        # Delete job record
        self._redis.delete(f"{self._job_prefix}{job_id}")
        
        return True


# Singleton instance
_job_queue: Optional[RedisJobQueue] = None


def get_job_queue() -> RedisJobQueue:
    """Get or create job queue instance"""
    global _job_queue
    if _job_queue is None:
        _job_queue = RedisJobQueue()
    return _job_queue

"""
Stats Service - Redis Client

Manages job queue operations for statistical analysis.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

import redis.asyncio as redis

from ..config import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    STATS_JOBS_PENDING,
    STATS_JOBS_PREFIX,
)

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for stats job management"""

    def __init__(self):
        self._pool = None

    async def connect(self):
        """Create connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
        return redis.Redis(connection_pool=self._pool)

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    async def create_job(
        self,
        job_type: str,
        params: dict,
        user_id: str,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Create a new stats job and add to queue.

        Args:
            job_type: Type of job (eda, tableone)
            params: Job parameters
            user_id: User identifier
            session_id: Optional session identifier

        Returns:
            Job information dict
        """
        client = await self.connect()

        job_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        job = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "pending",
            "params": params,
            "user_id": user_id,
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "progress": 0.0,
            "message": "Job queued",
        }

        # Store job metadata
        await client.set(
            f"{STATS_JOBS_PREFIX}{job_id}",
            json.dumps(job),
            ex=86400 * 7  # 7 days TTL
        )

        # Add to pending queue
        await client.lpush(STATS_JOBS_PENDING, json.dumps(job))

        logger.info(f"Created job {job_id} (type: {job_type}) for user {user_id}")

        return job

    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get job information by ID"""
        client = await self.connect()

        data = await client.get(f"{STATS_JOBS_PREFIX}{job_id}")

        if data:
            return json.loads(data)
        return None

    async def list_jobs(
        self,
        user_id: str,
        job_type: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """List jobs for a user"""
        client = await self.connect()

        # Scan for user's jobs
        # Note: This is a simple implementation. For production,
        # consider using Redis secondary indexes or a proper DB
        jobs = []
        cursor = 0

        while True:
            cursor, keys = await client.scan(
                cursor,
                match=f"{STATS_JOBS_PREFIX}*",
                count=100
            )

            for key in keys:
                data = await client.get(key)
                if data:
                    job = json.loads(data)
                    if job.get("user_id") == user_id:
                        if job_type is None or job.get("job_type") == job_type:
                            jobs.append(job)

            if cursor == 0:
                break

        # Sort by created_at descending
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return jobs[:limit]

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a job (only if owned by user)"""
        client = await self.connect()

        job = await self.get_job(job_id)
        if not job or job.get("user_id") != user_id:
            return False

        await client.delete(f"{STATS_JOBS_PREFIX}{job_id}")
        return True

    # =========================================================================
    # Generic Redis Operations (for result storage)
    # =========================================================================

    async def set(self, key: str, value: str, ex: int = None) -> None:
        """Set a key-value pair with optional TTL"""
        client = await self.connect()
        await client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        client = await self.connect()
        return await client.get(key)

    async def delete(self, key: str) -> int:
        """Delete a key"""
        client = await self.connect()
        return await client.delete(key)

    async def scan_iter(self, match: str = "*", count: int = 100):
        """Iterate over keys matching a pattern"""
        client = await self.connect()
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=match, count=count)
            for key in keys:
                yield key
            if cursor == 0:
                break


# Singleton instance
redis_client = RedisClient()

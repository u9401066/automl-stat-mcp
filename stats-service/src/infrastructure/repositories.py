"""
Stats Job Repository - Redis Implementation

Infrastructure layer implementation of StatsJobRepository interface.
"""
import json
import logging
from typing import List, Optional

import redis.asyncio as redis

from ..config import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    STATS_JOBS_PENDING,
    STATS_JOBS_PREFIX,
)
from ..domain.models import StatsJob, StatsJobId
from ..domain.repositories import StatsJobRepository

logger = logging.getLogger(__name__)


class RedisStatsJobRepository(StatsJobRepository):
    """Redis implementation of StatsJobRepository"""

    def __init__(self):
        self._client = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client"""
        if self._client is None:
            self._client = redis.Redis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
        return self._client

    async def save(self, job: StatsJob) -> None:
        """Save a job"""
        client = await self._get_client()

        job_data = job.to_dict()

        # Store job metadata
        await client.set(
            f"{STATS_JOBS_PREFIX}{job.id}",
            json.dumps(job_data),
            ex=86400 * 7  # 7 days TTL
        )

        logger.info(f"Saved job {job.id} (type: {job.job_type.value})")

    async def get_by_id(self, job_id: StatsJobId) -> Optional[StatsJob]:
        """Get job by ID"""
        client = await self._get_client()

        data = await client.get(f"{STATS_JOBS_PREFIX}{job_id}")
        if not data:
            return None

        job_dict = json.loads(data)
        return StatsJob.from_dict(job_dict)

    async def find_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[StatsJob]:
        """Find all jobs for a user/session"""
        client = await self._get_client()

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
                    job_dict = json.loads(data)

                    # Filter by user
                    if job_dict.get("user_id") != user_id:
                        continue

                    # Filter by session if specified
                    if session_id and job_dict.get("session_id") != session_id:
                        continue

                    # Filter by job type if specified
                    if job_type and job_dict.get("job_type") != job_type:
                        continue

                    try:
                        jobs.append(StatsJob.from_dict(job_dict))
                    except Exception as e:
                        logger.warning(f"Failed to parse job: {e}")

            if cursor == 0:
                break

        # Sort by created_at descending
        jobs.sort(key=lambda x: x.created_at, reverse=True)

        return jobs[:limit]

    async def find_pending(self) -> List[StatsJob]:
        """Find all pending jobs"""
        client = await self._get_client()

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
                    job_dict = json.loads(data)
                    if job_dict.get("status") == "pending":
                        try:
                            jobs.append(StatsJob.from_dict(job_dict))
                        except Exception as e:
                            logger.warning(f"Failed to parse job: {e}")

            if cursor == 0:
                break

        return jobs

    async def update(self, job: StatsJob) -> None:
        """Update a job"""
        # Same as save for Redis
        await self.save(job)

    async def delete(self, job_id: StatsJobId) -> bool:
        """Delete a job"""
        client = await self._get_client()

        result = await client.delete(f"{STATS_JOBS_PREFIX}{job_id}")
        return result > 0


class RedisJobQueue:
    """Job queue for stats worker"""

    def __init__(self):
        self._pool = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
        return redis.Redis(connection_pool=self._pool)

    async def enqueue_job(self, job: StatsJob) -> None:
        """Add job to pending queue"""
        client = await self._get_client()

        job_data = job.to_dict()
        await client.lpush(STATS_JOBS_PENDING, json.dumps(job_data))

        logger.info(f"Enqueued job {job.id} to {STATS_JOBS_PENDING}")


# Singleton instances
_job_repo: Optional[RedisStatsJobRepository] = None
_job_queue: Optional[RedisJobQueue] = None


def get_job_repository() -> RedisStatsJobRepository:
    """Get job repository singleton"""
    global _job_repo
    if _job_repo is None:
        _job_repo = RedisStatsJobRepository()
    return _job_repo


def get_job_queue() -> RedisJobQueue:
    """Get job queue singleton"""
    global _job_queue
    if _job_queue is None:
        _job_queue = RedisJobQueue()
    return _job_queue

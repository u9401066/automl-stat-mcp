"""
Redis Connection Manager

Singleton pattern for managing Redis connections across all services.
Provides a unified connection pool to reduce resource usage and improve performance.

Usage:
    from shared.infrastructure.redis_manager import RedisManager

    # Get singleton instance
    manager = await RedisManager.get_instance()

    # Get Redis client from pool
    client = await manager.get_client()

    # Use client
    await client.set("key", "value")
    result = await client.get("key")
"""

import asyncio
import logging
import os
from inspect import isawaitable
from typing import Optional, cast

import redis as sync_redis
import redis.asyncio as redis
from redis.exceptions import ConnectionError

logger = logging.getLogger(__name__)

# Redis configuration from environment
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Connection pool configuration
MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "50"))
SOCKET_TIMEOUT = int(os.environ.get("REDIS_SOCKET_TIMEOUT", "5"))
SOCKET_CONNECT_TIMEOUT = int(os.environ.get("REDIS_CONNECT_TIMEOUT", "5"))


class RedisManager:
    """
    Singleton Redis connection manager.

    Manages a single connection pool shared across the entire application,
    reducing overhead and improving resource utilization.

    Features:
    - Singleton pattern (one instance per process)
    - Connection pool with configurable size
    - Automatic retry on connection failure
    - Thread-safe initialization
    - Graceful shutdown

    Example:
        manager = await RedisManager.get_instance()
        client = await manager.get_client()
        await client.set("key", "value")
    """

    _instance: Optional["RedisManager"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """
        Private constructor. Use get_instance() instead.
        """
        if RedisManager._instance is not None:
            raise RuntimeError("RedisManager is a singleton. Use RedisManager.get_instance() instead.")

        self._pool: Optional[redis.ConnectionPool] = None
        self._initialized = False

    @classmethod
    async def get_instance(cls) -> "RedisManager":
        """
        Get the singleton instance of RedisManager.

        Thread-safe initialization using asyncio.Lock.

        Returns:
            RedisManager: The singleton instance

        Raises:
            ConnectionError: If Redis connection fails after retries
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
                    cls._instance._pool = None
                    cls._instance._initialized = False
                    await cls._instance._initialize_pool()

        return cls._instance

    @classmethod
    async def reset_instance(cls):
        """
        Reset the singleton instance (for testing).

        Closes the existing pool and clears the instance.
        Use with caution in production.
        """
        async with cls._lock:
            if cls._instance is not None:
                await cls._instance.close()
                cls._instance = None

    async def _initialize_pool(self) -> None:
        """
        Initialize Redis connection pool with retry logic.

        Attempts to create connection pool up to 3 times with exponential backoff.

        Raises:
            ConnectionError: If all connection attempts fail
        """
        if self._initialized:
            return

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

                self._pool = redis.ConnectionPool.from_url(
                    redis_url,
                    decode_responses=True,
                    max_connections=MAX_CONNECTIONS,
                    socket_keepalive=True,
                    socket_connect_timeout=SOCKET_CONNECT_TIMEOUT,
                    socket_timeout=SOCKET_TIMEOUT,
                    retry_on_timeout=True,
                    health_check_interval=30,  # Health check every 30s
                )

                # Test connection
                test_client = redis.Redis(connection_pool=self._pool)
                ping_result = test_client.ping()
                if isawaitable(ping_result):
                    await ping_result

                self._initialized = True
                logger.info(
                    f"Redis connection pool initialized successfully "
                    f"(host={REDIS_HOST}, port={REDIS_PORT}, db={REDIS_DB}, "
                    f"max_connections={MAX_CONNECTIONS})"
                )
                return

            except ConnectionError as e:
                logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("Failed to initialize Redis connection pool after all retries")
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff

            except Exception as e:
                logger.error(f"Unexpected error initializing Redis pool: {e}")
                raise

    async def get_client(self) -> redis.Redis:
        """
        Get a Redis client from the connection pool.

        Returns:
            redis.Redis: Redis client connected to the pool

        Raises:
            RuntimeError: If connection pool is not initialized
            ConnectionError: If unable to get connection from pool

        Example:
            manager = await RedisManager.get_instance()
            client = await manager.get_client()
            await client.set("key", "value")
        """
        if not self._initialized or self._pool is None:
            await self._initialize_pool()

        try:
            return redis.Redis(connection_pool=self._pool)
        except Exception as e:
            logger.error(f"Failed to get Redis client from pool: {e}")
            raise

    async def ping(self) -> bool:
        """
        Test Redis connection.

        Returns:
            bool: True if connection is alive, False otherwise
        """
        try:
            client = await self.get_client()
            result = client.ping()
            if isawaitable(result):
                return bool(await result)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def close(self) -> None:
        """
        Close the connection pool and release resources.

        Should be called during application shutdown.

        Example:
            manager = await RedisManager.get_instance()
            await manager.close()
        """
        if self._pool is not None:
            try:
                close_result = self._pool.aclose()
                if isawaitable(close_result):
                    await close_result
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")
            finally:
                self._pool = None
                self._initialized = False

    def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics.

        Returns:
            dict: Pool statistics including max_connections and current usage
        """
        if self._pool is None:
            return {"initialized": False, "max_connections": 0, "connection_kwargs": {}}

        return {
            "initialized": self._initialized,
            "max_connections": MAX_CONNECTIONS,
            "connection_kwargs": {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "socket_timeout": SOCKET_TIMEOUT,
                "socket_connect_timeout": SOCKET_CONNECT_TIMEOUT,
            },
        }


# Convenience function for getting Redis client
async def get_redis_client() -> redis.Redis:
    """
    Convenience function to get a Redis client.

    Returns:
        redis.Redis: Redis client from the shared connection pool

    Example:
        from shared.infrastructure.redis_manager import get_redis_client

        client = await get_redis_client()
        await client.set("key", "value")
    """
    manager = await RedisManager.get_instance()
    return await manager.get_client()


# Convenience function for sync clients (e.g., stats-service/automl-service)
def get_sync_client() -> sync_redis.Redis:
    """
    Get synchronous Redis client from shared connection pool.

    For services that use sync Redis operations (non-async).

    Returns:
        redis.Redis: Synchronous Redis client

    Example:
        ```python
        client = get_sync_client()
        client.set("key", "value")
        data = client.get("key")
        ```

    Note:
        This creates a sync client from the async connection pool config.
        The sync client will create its own connection pool lazily.
    """
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    return cast(
        sync_redis.Redis,
        sync_redis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=MAX_CONNECTIONS,
            socket_keepalive=True,
            socket_connect_timeout=SOCKET_CONNECT_TIMEOUT,
            socket_timeout=SOCKET_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=30,
        ),
    )

"""
Unit Tests for RedisManager

Tests the singleton Redis connection manager.
"""

import asyncio
import os

# Add parent directory to path for imports
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.infrastructure.redis_manager import RedisManager, get_redis_client


@pytest.fixture(autouse=True)
async def reset_singleton():
    """Reset singleton before each test"""
    await RedisManager.reset_instance()
    yield
    await RedisManager.reset_instance()


class TestRedisManagerSingleton:
    """Test singleton pattern implementation"""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that only one instance is created"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager1 = await RedisManager.get_instance()
                manager2 = await RedisManager.get_instance()

                assert manager1 is manager2
                assert mock_pool.call_count == 1  # Pool created only once

    @pytest.mark.asyncio
    async def test_multiple_concurrent_initialization(self):
        """Test that concurrent access creates only one instance"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                # Create multiple concurrent requests
                tasks = [RedisManager.get_instance() for _ in range(10)]
                managers = await asyncio.gather(*tasks)

                # All should be the same instance
                assert all(m is managers[0] for m in managers)
                assert mock_pool.call_count == 1  # Pool created only once

    @pytest.mark.asyncio
    async def test_reset_instance(self):
        """Test resetting the singleton instance"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.aclose = AsyncMock()
            mock_pool.return_value = mock_pool_instance

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager1 = await RedisManager.get_instance()
                await RedisManager.reset_instance()
                manager2 = await RedisManager.get_instance()

                assert manager1 is not manager2
                assert mock_pool_instance.aclose.called


class TestRedisManagerConnection:
    """Test connection management"""

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self):
        """Test connection pool is initialized correctly"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                await RedisManager.get_instance()

                # Check pool was created with correct parameters
                mock_pool.assert_called_once()
                call_kwargs = mock_pool.call_args[1]

                assert call_kwargs["decode_responses"] is True
                assert call_kwargs["max_connections"] == int(os.environ.get("REDIS_MAX_CONNECTIONS", "50"))
                assert call_kwargs["socket_keepalive"] is True
                assert call_kwargs["retry_on_timeout"] is True

    @pytest.mark.asyncio
    async def test_connection_retry_on_failure(self):
        """Test connection retry logic"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            # Fail twice, then succeed
            mock_pool.side_effect = [
                redis.ConnectionError("Connection failed"),
                redis.ConnectionError("Connection failed"),
                MagicMock(),
            ]

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                await RedisManager.get_instance()

                # Should have retried 3 times
                assert mock_pool.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_failure_after_retries(self):
        """Test that connection failure raises after all retries"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.side_effect = redis.ConnectionError("Connection failed")

            with pytest.raises(redis.ConnectionError):
                await RedisManager.get_instance()

    @pytest.mark.asyncio
    async def test_ping_success(self):
        """Test successful ping"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()
                result = await manager.ping()

                assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        """Test ping failure handling"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                # First ping for initialization succeeds, second ping fails
                mock_ping.side_effect = [True, redis.ConnectionError("Ping failed")]

                manager = await RedisManager.get_instance()
                result = await manager.ping()

                assert result is False


class TestRedisManagerClient:
    """Test Redis client operations"""

    @pytest.mark.asyncio
    async def test_get_client(self):
        """Test getting a Redis client from pool"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()
                client = await manager.get_client()

                assert isinstance(client, redis.Redis)

    @pytest.mark.asyncio
    async def test_multiple_clients_same_pool(self):
        """Test that multiple clients use the same connection pool"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()

                # Get multiple clients
                client1 = await manager.get_client()
                client2 = await manager.get_client()
                client3 = await manager.get_client()

                # All should use the same pool
                assert client1.connection_pool is mock_pool_instance
                assert client2.connection_pool is mock_pool_instance
                assert client3.connection_pool is mock_pool_instance

    @pytest.mark.asyncio
    async def test_get_redis_client_convenience_function(self):
        """Test convenience function for getting client"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                client = await get_redis_client()

                assert isinstance(client, redis.Redis)


class TestRedisManagerCleanup:
    """Test cleanup and resource management"""

    @pytest.mark.asyncio
    async def test_close_pool(self):
        """Test closing the connection pool"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.aclose = AsyncMock()
            mock_pool.return_value = mock_pool_instance

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()
                await manager.close()

                mock_pool_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pool_stats(self):
        """Test getting pool statistics"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()
                stats = manager.get_pool_stats()

                assert stats["initialized"] is True
                assert "max_connections" in stats
                assert "connection_kwargs" in stats
                assert stats["connection_kwargs"]["host"] == os.environ.get("REDIS_HOST", "localhost")

    @pytest.mark.asyncio
    async def test_get_pool_stats_before_init(self):
        """Test getting pool stats before initialization"""
        manager = RedisManager.__new__(RedisManager)
        manager._pool = None
        manager._initialized = False

        stats = manager.get_pool_stats()

        assert stats["initialized"] is False
        assert stats["max_connections"] == 0


class TestRedisManagerErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_direct_instantiation_raises_error(self):
        """Test that singleton pattern is enforced"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager1 = await RedisManager.get_instance()
                manager2 = await RedisManager.get_instance()
                assert manager1 is manager2  # Singleton verified

    @pytest.mark.asyncio
    async def test_get_client_before_init(self):
        """Test getting client auto-initializes pool"""
        with patch.object(redis.ConnectionPool, "from_url") as mock_pool:
            mock_pool.return_value = MagicMock()

            with patch.object(redis.Redis, "ping", new_callable=AsyncMock) as mock_ping:
                mock_ping.return_value = True

                manager = await RedisManager.get_instance()
                # Manually clear pool to test auto-init
                manager._pool = None
                manager._initialized = False

                client = await manager.get_client()

                # Should have re-initialized
                assert isinstance(client, redis.Redis)
                assert manager._initialized is True

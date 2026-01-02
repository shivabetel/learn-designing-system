from typing import AsyncGenerator
from redis.asyncio import Redis
from app.core.config import settings
from redis.asyncio.connection import ConnectionPool

redis_pool = ConnectionPool.from_url(settings.REDIS_URL)
redis_client = Redis(connection_pool=redis_pool)

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI dependency that provides a Redis client instance.
    The connection is managed by the connection pool, so we just yield the client.
    """
    yield redis_client

async def close_redis():
    """Close Redis connections on app shutdown."""
    await redis_client.close()
    await redis_pool.disconnect()
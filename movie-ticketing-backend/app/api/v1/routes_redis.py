from redis.asyncio import Redis
from fastapi import APIRouter, Depends

from app.redis import get_redis

router = APIRouter(
    prefix="/redis"
)


@router.post("/set-cache")
async def set_cache(key: str, value: str, redis: Redis = Depends(get_redis)):
    await redis.set(key, value, ex="300")


@router.get("/get-cache")
async def get_cache(key: str, redis: Redis = Depends(get_redis)):
    return await redis.get(key)

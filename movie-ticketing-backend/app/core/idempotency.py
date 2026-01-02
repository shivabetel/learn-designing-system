import json
from redis.asyncio import Redis
from fastapi import HTTPException, Request


async def check_idempotency(request: Request, redis: Redis):
    idem_key = request.headers.get("X-Idempotency-Key")
    if not idem_key:
        raise HTTPException(400, "Missing Idempotency Key")
    redis_key = f"idempotency:{idem_key}"
    cached = await redis.get(redis_key)
    if cached:
        return idem_key, json.loads(cached), True
    return idem_key, None, False

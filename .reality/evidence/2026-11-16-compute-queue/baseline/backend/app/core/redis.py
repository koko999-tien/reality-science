from redis.asyncio import Redis, from_url
from app.core.config import settings

redis_client: Redis | None = None
redis_result_client: Redis | None = None


async def get_redis_client() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return redis_client


async def get_redis_result_client() -> Redis:
    global redis_result_client
    if redis_result_client is None:
        redis_result_client = from_url(
            settings.celery_result_backend_url, encoding="utf-8", decode_responses=True
        )
    return redis_result_client


async def close_redis_client() -> None:
    global redis_client, redis_result_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
    if redis_result_client is not None:
        await redis_result_client.close()
        redis_result_client = None

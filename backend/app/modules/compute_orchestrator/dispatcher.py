import json
from app.core.redis import get_redis_client
from shared.schemas.job_bundle import JobBundle


async def dispatch_compute_job(bundle: JobBundle) -> str:
    """Dispatches a typed JobBundle to Redis compute_tasks Celery queue."""
    redis = await get_redis_client()
    payload = {
        "id": bundle.job_id,
        "task": "worker.tasks.verify_equation_ast",
        "args": [bundle.model_dump()],
        "kwargs": {},
        "retries": 0,
    }
    await redis.lpush("compute_tasks", json.dumps(payload))
    return bundle.job_id

import json
from app.core.redis import get_redis_client
from shared.schemas.finding_result import FindingResult


async def fetch_finding_result(job_id: str) -> FindingResult | None:
    """Retrieves finding result from Redis result backend by job_id."""
    redis = await get_redis_client()
    key = f"celery-task-meta-{job_id}"
    raw = await redis.get(key)
    if not raw:
        return None
    data = json.loads(raw)
    result_dict = data.get("result", {})
    return FindingResult.model_validate(result_dict)

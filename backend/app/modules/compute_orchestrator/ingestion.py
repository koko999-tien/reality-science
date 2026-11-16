import json
from pydantic import ValidationError
from app.core.redis import get_redis_result_client
from app.modules.compute_orchestrator.errors import ComputeUnavailable, InvalidComputeResult
from shared.schemas.finding_result import FindingResult


async def fetch_finding_result(job_id: str) -> FindingResult | None:
    """Retrieves finding result from Redis result backend (DB 1) by job_id."""
    redis = await get_redis_result_client()
    key = f"celery-task-meta-{job_id}"
    raw = await redis.get(key)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("task_id") != job_id:
            raise InvalidComputeResult("Celery result task identity mismatch")
        if data.get("status") in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
            return None
        if data.get("status") in {"FAILURE", "REVOKED"}:
            raise ComputeUnavailable("Compute task failed or expired")
        if data.get("status") != "SUCCESS":
            raise InvalidComputeResult("Unknown Celery result status")
        finding = FindingResult.model_validate(data.get("result"))
        if finding.job_id != job_id:
            raise InvalidComputeResult("Finding job identity mismatch")
        return finding
    except (ValueError, TypeError, ValidationError) as exc:
        raise InvalidComputeResult("Malformed compute result") from exc


async def discard_finding_result(job_id: str) -> None:
    redis = await get_redis_result_client()
    await redis.delete(f"celery-task-meta-{job_id}")

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from app.core.redis import get_redis_client
from app.modules.compute_orchestrator.errors import ComputeUnavailable
from shared.schemas.job_bundle import JobBundle


async def dispatch_compute_job(bundle: JobBundle) -> str:
    """Dispatches a typed JobBundle to Redis compute_tasks Celery queue formatted with
    standard Celery/Kombu envelope headers, properties, and base64-encoded payload.
    """
    redis = await get_redis_client()
    task_id = bundle.job_id
    args = [bundle.model_dump(mode="json")]
    kwargs = {}
    body = [args, kwargs, {"callbacks": None, "errbacks": None, "chain": None, "chord": None}]
    encoded_body = json.dumps(body, allow_nan=False).encode("utf-8")
    if len(encoded_body) > 10 * 1024 * 1024:
        raise ComputeUnavailable("Compute payload exceeds the queue limit")
    body_b64 = base64.b64encode(encoded_body).decode("utf-8")

    envelope = {
        "body": body_b64,
        "headers": {
            "lang": "py",
            "task": "worker.tasks.verify_equation_ast",
            "id": task_id,
            "root_id": task_id,
            "parent_id": None,
            "group": None,
            "argsrepr": f"[JobBundle(job_id='{task_id}')]",
            "kwargsrepr": "{}",
            "origin": "backend@reality_science",
            "retries": 0,
            "expires": (datetime.now(timezone.utc) + timedelta(seconds=bundle.timeout_seconds + 5)).isoformat(),
            # Celery v2 consumer expects (hard, soft), as emitted by as_task_v2.
            "timelimit": [bundle.timeout_seconds + 5, bundle.timeout_seconds],
        },
        "content-type": "application/json",
        "properties": {
            "correlation_id": task_id,
            "reply_to": str(uuid.uuid4()),
            "delivery_mode": 2,
            "delivery_info": {
                "exchange": "",
                "routing_key": "compute_tasks",
            },
            "priority": 0,
            "body_encoding": "base64",
            "delivery_tag": str(uuid.uuid4()),
        },
        "content-encoding": "utf-8",
    }
    # A server-generated job ID is single-use, even after timeout/failed publish.
    # Retain the tombstone longer than both Celery result and visibility TTLs.
    claimed = await redis.set(f"compute-dispatched:{task_id}", bundle.fingerprint(), nx=True, ex=86400)
    if not claimed:
        raise ComputeUnavailable("Compute job ID has already been dispatched")
    await redis.lpush("compute_tasks", json.dumps(envelope))
    return task_id

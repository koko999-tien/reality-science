import base64
import json
import uuid
from app.core.redis import get_redis_client
from shared.schemas.job_bundle import JobBundle


async def dispatch_compute_job(bundle: JobBundle) -> str:
    """Dispatches a typed JobBundle to Redis compute_tasks Celery queue formatted with
    standard Celery/Kombu envelope headers, properties, and base64-encoded payload.
    """
    redis = await get_redis_client()
    task_id = bundle.job_id
    args = [bundle.model_dump()]
    kwargs = {}
    body = [args, kwargs, {"callbacks": None, "errbacks": None, "chain": None, "chord": None}]
    body_b64 = base64.b64encode(json.dumps(body).encode("utf-8")).decode("utf-8")

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
    await redis.lpush("compute_tasks", json.dumps(envelope))
    return task_id

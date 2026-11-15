from celery import Celery
from worker.config import get_worker_settings

settings = get_worker_settings()

celery_app = Celery(
    "reality_science_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks.compute_tasks", "worker.tasks.epistemic"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="compute_tasks",
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=settings.interactive_timeout_seconds,
    task_time_limit=settings.interactive_timeout_seconds + 5,
)

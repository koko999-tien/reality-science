"""Real isolated worker; test-only deterministic pause before actual computation."""
import importlib.util
import json
import os
from pathlib import Path
import sys

from worker.config import assert_zero_database_credentials
assert_zero_database_credentials()
drivers = [name for name in ["asyncpg", "psycopg", "psycopg2", "sqlalchemy"] if importlib.util.find_spec(name)]
assert not drivers
E = Path(__file__).resolve().parent
name = os.environ["REALITY_TEST_RUN"]
(E / f"{name}-worker-identity.json").write_text(json.dumps({"pid": os.getpid(), "database_env_guard": "PASS", "database_drivers_present": drivers, "environment_keys": sorted(os.environ)}, indent=2))


def audit(event, args):
    if event == "socket.connect":
        with (E / f"{name}-worker-connections.jsonl").open("a") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "address": args[1]}) + "\n")


sys.addaudithook(audit)
from redis import Redis
from celery.signals import task_prerun, task_postrun
from worker.celery_app import celery_app


@task_prerun.connect
def capture_input(task_id=None, args=None, **kwargs):
    bundle = args[0]
    with (E / f"{name}-worker-inputs.jsonl").open("a") as stream:
        stream.write(json.dumps({"job_id": task_id, "bundle": bundle}) + "\n")
    broker = Redis.from_url(os.environ["CELERY_BROKER_URL"])
    try:
        key = "draft-test-hold:" + bundle["version_id"]
        if broker.get(key):
            broker.set(key + ":started", task_id, ex=60)
            broker.blpop(key + ":release", timeout=8)
    finally:
        broker.close()


@task_postrun.connect
def capture_result(task_id=None, retval=None, **kwargs):
    with (E / f"{name}-worker-results.jsonl").open("a") as stream:
        stream.write(json.dumps({"job_id": task_id, "result": retval}) + "\n")


celery_app.worker_main(["worker", "--pool=solo", "--concurrency=1", "--loglevel=WARNING", "--without-gossip", "--without-mingle", "--without-heartbeat", "--queues=compute_tasks", "--hostname=draft-save@%h"])

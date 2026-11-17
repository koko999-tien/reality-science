"""Separate zero-DB worker; optional explicit exception injection for this evidence."""
import importlib.util
import json
import os
from pathlib import Path
import sys

E = Path(__file__).resolve().parent
name = os.environ['REALITY_TEST_RUN']
from worker.config import assert_zero_database_credentials
assert_zero_database_credentials()
drivers = [module for module in ['asyncpg', 'psycopg', 'psycopg2', 'sqlalchemy', 'pymysql', 'pymongo']
           if importlib.util.find_spec(module) is not None]
assert not drivers, drivers
(E / (name + '-worker-identity.json')).write_text(json.dumps({
    'pid': os.getpid(), 'executable': sys.executable, 'database_env_guard': 'PASS',
    'database_drivers_present': drivers, 'environment_keys': sorted(os.environ),
    'mode': 'Windows solo; explicit helper exception injection where named',
}, indent=2))


def audit(event, args):
    if event == 'socket.connect':
        with (E / (name + '-worker-connections.jsonl')).open('a') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'address': args[1]}) + '\n')


sys.addaudithook(audit)
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import task_success
from worker.celery_app import celery_app
from worker.core import boundary_engine
from worker.tasks import dimensional


def deadline(*args, **kwargs):
    with (E / (name + '-injection.jsonl')).open('a') as stream:
        stream.write(json.dumps({'mode': name, 'pid': os.getpid(), 'exception': 'SoftTimeLimitExceeded',
                                'job_id': current_task.request.id}) + '\n')
    raise SoftTimeLimitExceeded()


if name == 'soft-dimensions':
    dimensional.evaluate_ast_dimensions = deadline
elif name == 'soft-limit':
    boundary_engine.sp.limit = deadline


@task_success.connect(weak=False)
def record_result(sender=None, result=None, **kwargs):
    with (E / (name + '-worker-results.jsonl')).open('a') as stream:
        stream.write(json.dumps(result) + '\n')


celery_app.worker_main(['worker', '--pool=solo', '--concurrency=1', '--loglevel=WARNING',
                       '--without-gossip', '--without-mingle', '--without-heartbeat',
                       '--hostname=reality-review-local@%h', '--queues=compute_tasks'])

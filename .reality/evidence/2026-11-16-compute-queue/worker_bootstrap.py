"""Actual Celery worker; records host isolation evidence without environment values."""
import importlib.util
import json
import os
from pathlib import Path
import sys

E=Path(__file__).resolve().parent
run=os.environ['REALITY_TEST_RUN']
from worker.config import assert_zero_database_credentials
assert_zero_database_credentials()
drivers=['asyncpg','psycopg','psycopg2','sqlalchemy','pymysql','pymongo']
available=[name for name in drivers if importlib.util.find_spec(name) is not None]
assert not available, available
(E/(run+'-worker-identity.json')).write_text(json.dumps({'pid':os.getpid(),'executable':sys.executable,
    'database_env_guard':'PASS','database_drivers_present':available,
    'environment_keys':sorted(os.environ),'mode':'real Celery solo, local Windows only'},indent=2))


def audit(event,args):
    if event=='socket.connect':
        address=args[1]
        with (E/(run+'-worker-connections.jsonl')).open('a') as stream:
            stream.write(json.dumps({'pid':os.getpid(),'address':address})+'\n')


sys.addaudithook(audit)
from worker.celery_app import celery_app
celery_app.worker_main(['worker','--pool=solo','--concurrency=1','--loglevel=WARNING',
                        '--without-gossip','--without-mingle','--without-heartbeat',
                        '--hostname=reality-compute-local@%h','--queues=compute_tasks'])

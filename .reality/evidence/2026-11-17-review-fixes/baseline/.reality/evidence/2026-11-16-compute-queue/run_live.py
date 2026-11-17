"""Bounded local lifecycle: checked PostgreSQL + fresh broker + separate real worker."""
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT=Path('D:/Reality_Science'); BACKEND=ROOT/'backend'; E=Path(__file__).resolve().parent
RUNTIME=Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-compute-queue-20261116')
WORKER=Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-worker-verification-20261116/Scripts/python.exe')
sys.path.insert(0,str(BACKEND))
from scripts.disposable_postgres import start_cluster, admin_connection, stop_cluster, environment, control_data
from redis import Redis


def stop_owned_process(process):
    if process is not None and process.poll() is None:
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],check=True,capture_output=True)
        process.wait(timeout=20)


def run(command,name,env):
    with (E/(name+'.log')).open('w',encoding='utf-8') as log:
        code=subprocess.run(command,cwd=BACKEND,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
    print((E/(name+'.log')).read_text(encoding='utf-8'))
    return {'command':command,'exit':code}


async def identity(manifest):
    conn,actual=await admin_connection(manifest)
    try:
        actual['revision']=await conn.fetchval('SELECT version_num FROM alembic_version')
        actual['roles']=[dict(row) for row in await conn.fetch(
            "SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname='rs_test_app'")]
        assert actual['revision']=='004_owner_only_dml'
        return actual
    finally: await conn.close()


def main():
    name=sys.argv[1] if len(sys.argv)>1 else 'live-original'
    if not re.fullmatch(r'[a-z0-9-]+',name): raise ValueError('Invalid evidence run name')
    tests=sys.argv[2:] or ['tests/integration/test_decision3_postgres_rls.py']
    if (E/(name+'.log')).exists(): raise RuntimeError('Refusing to overwrite prior run')
    manifest_path=E/'instance.json'; manifest=json.loads(manifest_path.read_text())
    broker=worker=None; client=None; broker_id=None; port=None; codes={}
    no_worker=os.environ.get('REALITY_TEST_NO_WORKER')=='1'
    logs=[]
    try:
        restart_evidence=E/(name+'-restart')
        restart_evidence.mkdir()
        start_cluster(manifest,manifest_path,restart_evidence)
        (E/(name+'-db-identity.json')).write_text(json.dumps(asyncio.run(identity(manifest)),indent=2))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        config=RUNTIME/(name+'-redis.conf')
        config.write_text(f'bind 127.0.0.1\nport {port}\nprotected-mode yes\nsave ""\nappendonly no\n'
                          'maxmemory 128mb\nmaxmemory-policy noeviction\n',encoding='utf-8')
        executable=next((RUNTIME/'broker').rglob('redis-server.exe'))
        cygpath='/cygdrive/'+config.drive[0].lower()+config.as_posix()[2:]
        log=(E/(name+'-broker.log')).open('w',encoding='utf-8'); logs.append(log)
        broker=subprocess.Popen([str(executable),cygpath],cwd=RUNTIME,stdout=log,stderr=subprocess.STDOUT)
        client=Redis(host='127.0.0.1',port=port,decode_responses=True,socket_timeout=2)
        deadline=time.monotonic()+15
        while True:
            if broker.poll() is not None: raise RuntimeError('Broker exited; inspect log')
            try:
                info=client.info('server')
                if info: break
            except Exception:
                if time.monotonic()>deadline: raise
                time.sleep(.1)
        broker_id=info['run_id']
        marker=name+'-'+broker_id
        client.set('reality-test-instance',marker)
        broker_identity={'pid_handle':broker.pid,'server':info,'config':client.config_get('bind','port','dir'),
                         'marker':marker,'executable':str(executable)}
        (E/(name+'-broker-identity.json')).write_text(json.dumps(broker_identity,indent=2))
        assert broker_identity['config']['bind']=='127.0.0.1' and int(info['tcp_port'])==port
        # Construct the worker environment independently. API retains its DB env.
        allow={'SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PATH',
               'NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','SYSTEMDRIVE'}
        worker_env={k:v for k,v in os.environ.items() if k.upper() in allow}
        worker_env.update(CELERY_BROKER_URL=f'redis://127.0.0.1:{port}/0',
                          CELERY_RESULT_BACKEND=f'redis://127.0.0.1:{port}/1',PYTHONIOENCODING='utf-8',
                          REALITY_TEST_RUN=name,
                          PYTHONPATH=os.pathsep.join([str(ROOT/'worker'),str(ROOT/'shared')]))
        if not no_worker:
            log=(E/(name+'-worker.log')).open('w',encoding='utf-8'); logs.append(log)
            worker=subprocess.Popen([str(WORKER),str(E/'worker_bootstrap.py')],cwd=RUNTIME,env=worker_env,
                                    stdout=log,stderr=subprocess.STDOUT)
        env=environment(manifest)
        env.update(REDIS_URL=f'redis://127.0.0.1:{port}/0',CELERY_RESULT_BACKEND_URL=f'redis://127.0.0.1:{port}/1',
                   REALITY_TEST_QUEUE_INSTANCE=marker)
        codes['tests']=run([sys.executable,'-m','pytest','-vv','--tb=short','--basetemp',str(E/(name+'-pytest')),
                            *tests],name,env)
        if worker is not None:
            assert worker.poll() is None, 'Worker exited unexpectedly'
        (E/(name+'-queue-after.json')).write_text(json.dumps({'queue_length':client.llen('compute_tasks'),
            'result_keys':Redis(host='127.0.0.1',port=port,db=1).keys('celery-task-meta-*').__len__(),
            'worker_still_running':worker is not None and worker.poll() is None,
            'worker_started':worker is not None},indent=2))
        return codes['tests']['exit']
    finally:
        stop_owned_process(worker)
        if broker is not None and broker.poll() is None:
            if broker_id is not None:
                assert client.info('server')['run_id']==broker_id
                assert client.get('reality-test-instance')==name+'-'+broker_id
                client.shutdown(nosave=True)
                broker.wait(timeout=15)
            else:
                stop_owned_process(broker)
        if client is not None: client.close()
        if not manifest.get('stopped'):
            asyncio.run(identity(manifest))
            codes['stop']=stop_cluster(manifest,E/(name+'-stop.log'))
            manifest_path.write_text(json.dumps(manifest,indent=2))
        for log in logs: log.close()
        ports={manifest['port']}
        if port: ports.add(port)
        for log in (E/(name+'-pytest')).glob('*/api.log'):
            ports.update(int(p) for p in re.findall(r'Uvicorn running on http://127\.0\.0\.1:(\d+)',log.read_text()))
        listening={}
        for p in ports:
            with socket.socket() as sock:
                sock.settimeout(.5); listening[str(p)]=sock.connect_ex(('127.0.0.1',p))==0
        cleanup={'codes':codes,'ports_accepting':listening,'postgres_stopped':manifest['stopped'],
                 'worker_exit':worker.poll() if worker else None,'broker_exit':broker.poll() if broker else None,
                 'postgres_control':control_data(manifest)}
        (E/(name+'-cleanup.json')).write_text(json.dumps(cleanup,indent=2))
        assert manifest['stopped'] and not any(listening.values())
        print(json.dumps(cleanup,indent=2))


if __name__=='__main__': raise SystemExit(main())

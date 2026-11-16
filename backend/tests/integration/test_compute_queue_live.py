"""Opt-in actual HTTP + Redis/Celery + PostgreSQL. No math/DB/auth overrides.

Version creation has no API contract: only fixture project/version rows are SQL seeded.
"""
import asyncio
import base64
import json
import os
import uuid

import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from tests.integration.test_decision3_postgres_rls import pg, live_api, register_login, context
from tests.postgres_target import disposable_target
from shared.schemas.job_bundle import JobBundle


@pytest.fixture(autouse=True)
def require_owned_queue():
    if not disposable_target(os.environ) or not os.environ.get("REALITY_TEST_QUEUE_INSTANCE"):
        pytest.skip("Explicit disposable database and task-owned queue required")


async def assert_queue_identity():
    broker=Redis.from_url(os.environ['REDIS_URL'],decode_responses=True)
    try:
        assert await broker.get('reality-test-instance')==os.environ['REALITY_TEST_QUEUE_INSTANCE']
    finally: await broker.aclose()


async def seed_version(pg,client,visibility="private_draft",publication="preprint"):
    headers,user=await register_login(client)
    version,project=(str(uuid.uuid4()) for _ in range(2))
    async with pg.begin() as conn:
        actor=(await conn.execute(text("SELECT id FROM research_actors WHERE user_account_id=:id"),{"id":user})).scalar_one()
        await context(conn,actor)
        await conn.execute(text("INSERT INTO research_projects(id,slug,title,owner_actor_id,visibility) "
            "VALUES (:id,:id,'Queue fixture',:actor,:visibility)"),{"id":project,"actor":actor,"visibility":visibility})
        await conn.execute(text("INSERT INTO research_versions(id,project_id,title,publication_status) "
            "VALUES (:id,:project,'Queue fixture',:publication)"),{"id":version,"project":project,"publication":publication})
    return headers,actor,version


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,expected", [("valid","PASS"),("undeclared","FAIL"),("dimensions","FAIL"),("zero","FAIL")])
async def test_interactive_uses_real_queue(live_api,kind,expected):
    await assert_queue_identity()
    variables=[{"symbol":"x","name":"position","unit":"m"}]
    ast={"node_type":"variable","value":"x"}
    if kind=="undeclared": variables=[]
    if kind=="dimensions":
        variables.append({"symbol":"t","name":"time","unit":"s"})
        ast={"node_type":"binary_op","op":"+","left":ast,"right":{"node_type":"variable","value":"t"}}
    if kind=="zero":
        ast={"node_type":"binary_op","op":"/","left":ast,"right":{"node_type":"constant","value":0}}
    response=await live_api.post('/api/v1/validation/verify',json={'expression_ast':ast,'variables':variables})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['state']==expected
    assert result['version_id']==result['target_entity_id']=='interactive'
    assert len(result['bundle_sha256'])==64 and len(result['layer_findings'])==6
    redis=Redis.from_url(os.environ['CELERY_RESULT_BACKEND_URL'])
    try: assert await redis.get('celery-task-meta-'+result['job_id']) is None
    finally: await redis.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility",["private_draft","public_preprint"])
@pytest.mark.parametrize("valid",[True,False])
async def test_queued_findings_read_after_new_request_and_connection(live_api,pg,visibility,valid,tmp_path):
    await assert_queue_identity()
    headers,actor,version=await seed_version(pg,live_api,visibility)
    outsiders,_=await register_login(live_api)
    route=f'/api/v1/versions/{version}'
    eq=await live_api.post(route+'/equations',headers=headers,json={'label':'Position','latex_raw':'x',
        'canonical_ast_json':{'node_type':'variable','value':'x'}})
    assert eq.status_code==201
    if valid:
        assert (await live_api.post(route+'/variables',headers=headers,json={
            'symbol':'x','name':'position','unit':'m'})).status_code==201
    expected='PASS' if valid else 'FAIL'
    result=await live_api.post(route+'/validate',headers=headers)
    assert result.status_code==200,result.text
    run=result.json()
    assert run['overall_state']==expected and len(run['findings'])==6
    assert all(f['run_id']==f['job_id']==run['id'] and f['target_entity_id']==eq.json()['id'] for f in run['findings'])
    assert all(f['diagnostics']['provenance']['version_id']==version for f in run['findings'])
    history=await live_api.get(route+'/validation-runs',headers=headers)
    assert history.status_code==200 and history.json()[0]==run
    for reader in ({},outsiders):
        assert (await live_api.get(route+'/validation-runs',headers=reader)).status_code==(200 if visibility=='public_preprint' else 404)
    assert (await live_api.post(route+'/validate',headers=outsiders)).status_code==404
    async with pg.begin() as fresh:
        await context(fresh,actor)
        assert (await fresh.execute(text('SELECT overall_state FROM validation_runs WHERE id=:id'),{'id':run['id']})).scalar_one()==expected
        assert (await fresh.execute(text('SELECT count(*) FROM validation_findings WHERE run_id=:id'),{'id':run['id']})).scalar_one()==6
        assert (await fresh.execute(text('SELECT publication_status FROM research_versions WHERE id=:id'),{'id':version})).scalar_one()=='preprint'
    (tmp_path/'run-evidence.json').write_text(json.dumps(run,indent=2))


@pytest.mark.asyncio
async def test_queue_without_worker_times_out_without_persistence(live_api,pg):
    if os.environ.get('REALITY_TEST_NO_WORKER')!='1':
        pytest.skip('Separate deliberate no-worker lifecycle required')
    await assert_queue_identity()
    headers,actor,version=await seed_version(pg,live_api)
    response=await live_api.post(f'/api/v1/versions/{version}/validate',headers=headers)
    assert response.status_code==503,response.text
    history=await live_api.get(f'/api/v1/versions/{version}/validation-runs',headers=headers)
    assert history.status_code==200 and history.json()==[]
    async with pg.begin() as fresh:
        await context(fresh,actor)
        assert (await fresh.execute(text('SELECT count(*) FROM validation_runs WHERE version_id=:id'),{'id':version})).scalar_one()==0
        assert (await fresh.execute(text('SELECT publication_status FROM research_versions WHERE id=:id'),{'id':version})).scalar_one()=='preprint'


def require_no_worker():
    if os.environ.get('REALITY_TEST_NO_WORKER')!='1':
        pytest.skip('Fault injection requires an isolated lifecycle without a worker')


async def receive_staged_bundle(broker):
    queued=await broker.brpop('compute_tasks',timeout=5)
    assert queued is not None,'HTTP API did not dispatch a job'
    message=json.loads(queued[1])
    args,kwargs,_=json.loads(base64.b64decode(message['body']))
    bundle=JobBundle.model_validate(args[0])
    assert message['headers']['id']==message['properties']['correlation_id']==bundle.job_id
    assert kwargs=={}
    return bundle


def protocol_fixture(bundle):
    """Deliberately synthetic envelope for rejection tests; never compute evidence."""
    return {'task_id':bundle.job_id,'status':'SUCCESS','result':{
        'job_id':bundle.job_id,'version_id':bundle.version_id,
        'target_entity_type':bundle.target_entity_type.value,'target_entity_id':bundle.target_entity_id,
        'bundle_sha256':bundle.fingerprint(),'state':'PASS','diagnostic_code':'PROTOCOL_FIXTURE',
        'message':'Synthetic protocol rejection fixture','dimensions_verified':False,
        'layer_findings':{str(i):{'layer':i,'name':str(i),'state':'PASS',
            'diagnostic_code':'PROTOCOL_FIXTURE','message':'Synthetic fixture'} for i in range(1,7)}}}


async def assert_no_persisted_run(live_api,pg,headers,actor,version):
    history=await live_api.get(f'/api/v1/versions/{version}/validation-runs',headers=headers)
    assert history.status_code==200 and history.json()==[]
    async with pg.begin() as fresh:
        await context(fresh,actor)
        assert (await fresh.execute(text('SELECT count(*) FROM validation_runs WHERE version_id=:id'),
                                    {'id':version})).scalar_one()==0
        assert (await fresh.execute(text('SELECT publication_status FROM research_versions WHERE id=:id'),
                                    {'id':version})).scalar_one()=='preprint'


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['bad-json','task','job','version','target','hash','layers','failure','revoked'])
async def test_fault_result_is_rejected_without_persistence(live_api,pg,fault,tmp_path):
    require_no_worker()
    await assert_queue_identity()
    headers,actor,version=await seed_version(pg,live_api)
    broker=Redis.from_url(os.environ['REDIS_URL'])
    results=Redis.from_url(os.environ['CELERY_RESULT_BACKEND_URL'])
    request=asyncio.create_task(live_api.post(f'/api/v1/versions/{version}/validate',headers=headers))
    try:
        bundle=await receive_staged_bundle(broker)
        envelope=protocol_fixture(bundle)
        if fault=='task': envelope['task_id']=str(uuid.uuid4())
        if fault=='job': envelope['result']['job_id']=str(uuid.uuid4())
        if fault=='version': envelope['result']['version_id']=str(uuid.uuid4())
        if fault=='target': envelope['result']['target_entity_id']=str(uuid.uuid4())
        if fault=='hash': envelope['result']['bundle_sha256']='0'*64
        if fault=='layers': del envelope['result']['layer_findings']['6']
        if fault in {'failure','revoked'}: envelope['status']=fault.upper()
        raw='{' if fault=='bad-json' else json.dumps(envelope)
        key='celery-task-meta-'+bundle.job_id
        await results.set(key,raw,ex=60)
        response=await request
        assert response.status_code==503,response.text
        assert await results.get(key) is None
        await assert_no_persisted_run(live_api,pg,headers,actor,version)
        (tmp_path/'fault-evidence.json').write_text(json.dumps({
            'kind':fault,'injected':True,'job_id':bundle.job_id,'version_id':version,
            'response_status':response.status_code,'persisted_runs':0,'result_key_removed':True},indent=2))
    finally:
        if not request.done(): request.cancel()
        await asyncio.gather(request,return_exceptions=True)
        await broker.aclose()
        await results.aclose()


@pytest.mark.asyncio
async def test_fault_late_result_cannot_attach_to_a_new_job(live_api,pg,tmp_path):
    require_no_worker()
    await assert_queue_identity()
    headers,actor,version=await seed_version(pg,live_api)
    broker=Redis.from_url(os.environ['REDIS_URL'])
    results=Redis.from_url(os.environ['CELERY_RESULT_BACKEND_URL'])
    request=asyncio.create_task(live_api.post(f'/api/v1/versions/{version}/validate',headers=headers))
    old_key=None
    try:
        old=await receive_staged_bundle(broker)
        assert (await request).status_code==503
        old_key='celery-task-meta-'+old.job_id
        await results.set(old_key,json.dumps(protocol_fixture(old)),ex=60)
        await assert_no_persisted_run(live_api,pg,headers,actor,version)
        request=asyncio.create_task(live_api.post(f'/api/v1/versions/{version}/validate',headers=headers))
        new=await receive_staged_bundle(broker)
        assert new.job_id!=old.job_id
        assert await results.get(old_key) is not None
        # Even moving the old result into the new key cannot bypass correlation.
        new_key='celery-task-meta-'+new.job_id
        await results.set(new_key,json.dumps(protocol_fixture(old)),ex=60)
        assert (await request).status_code==503
        assert await results.get(new_key) is None
        await assert_no_persisted_run(live_api,pg,headers,actor,version)
        (tmp_path/'late-evidence.json').write_text(json.dumps({
            'injected':True,'expired_job':old.job_id,'new_job':new.job_id,
            'persisted_runs':0,'both_responses':503,'late_result_ttl':await results.ttl(old_key)},indent=2))
    finally:
        if not request.done(): request.cancel()
        await asyncio.gather(request,return_exceptions=True)
        if old_key: await results.delete(old_key)
        await broker.aclose()
        await results.aclose()


@pytest.mark.asyncio
async def test_fault_duplicate_dispatch_is_claimed_once(tmp_path):
    require_no_worker()
    await assert_queue_identity()
    from app.core.redis import close_redis_client
    from app.modules.compute_orchestrator.dispatcher import dispatch_compute_job
    from app.modules.compute_orchestrator.errors import ComputeUnavailable
    bundle=JobBundle(job_id=str(uuid.uuid4()),version_id='fixture',target_entity_type='EQUATION',target_entity_id='fixture')
    broker=Redis.from_url(os.environ['REDIS_URL'])
    try:
        assert await broker.llen('compute_tasks')==0
        await dispatch_compute_job(bundle)
        with pytest.raises(ComputeUnavailable,match='already'):
            await dispatch_compute_job(bundle)
        assert await broker.llen('compute_tasks')==1
        staged=await receive_staged_bundle(broker)
        assert staged.job_id==bundle.job_id
        assert await broker.llen('compute_tasks')==0
        claim='compute-dispatched:'+bundle.job_id
        assert (await broker.get(claim)).decode()==bundle.fingerprint()
        ttl=await broker.ttl(claim)
        assert 86000<ttl<=86400
        (tmp_path/'replay-evidence.json').write_text(json.dumps({
            'job_id':bundle.job_id,'published_count':1,'duplicate_rejected':True,'claim_ttl':ttl},indent=2))
    finally:
        await broker.aclose()
        await close_redis_client()

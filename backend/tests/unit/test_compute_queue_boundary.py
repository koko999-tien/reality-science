"""Protocol/negative tests use Redis mocks; real queue evidence is separate."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.modules.compute_orchestrator import dispatcher, ingestion, service
from app.modules.compute_orchestrator.errors import ComputeUnavailable, ComputeTimeout, InvalidComputeResult
from shared.schemas.finding_result import FindingResult, LayerFinding
from shared.schemas.job_bundle import JobBundle


@pytest.fixture
def bundle():
    return JobBundle(job_id="test-job", version_id="version-a", target_entity_type="EQUATION",
                     target_entity_id="eq-a", expression_ast={"node_type":"constant","value":2})


def result_for(bundle):
    return FindingResult(job_id=bundle.job_id, version_id=bundle.version_id,
        target_entity_type=bundle.target_entity_type, target_entity_id=bundle.target_entity_id,
        bundle_sha256=bundle.fingerprint(), state="PASS", diagnostic_code="VALIDATION_PASSED",
        message="Test protocol fixture only", dimensions_verified=True,
        layer_findings={i:LayerFinding(layer=i,name=str(i),state="PASS",diagnostic_code="OK",message="fixture")
                        for i in range(1,7)})


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["bad-json","array","task","job","state","missing","failure","revoked"])
async def test_ingestion_rejects_invalid_or_failed_results(bundle, monkeypatch, mutation):
    data = {"task_id":bundle.job_id,"status":"SUCCESS","result":result_for(bundle).model_dump(mode="json")}
    if mutation == "task": data["task_id"]="other"
    if mutation == "job": data["result"]["job_id"]="other"
    if mutation == "state": data["result"]["state"]="VERIFIED"
    if mutation == "missing": del data["result"]
    if mutation in {"failure","revoked"}: data["status"]=mutation.upper()
    raw = "{" if mutation == "bad-json" else "[]" if mutation == "array" else json.dumps(data)
    redis = AsyncMock(); redis.get.return_value=raw
    monkeypatch.setattr(ingestion,"get_redis_result_client",AsyncMock(return_value=redis))
    with pytest.raises(ComputeUnavailable): await ingestion.fetch_finding_result(bundle.job_id)


@pytest.mark.parametrize("field", ["job_id","version_id","target_entity_id","target_entity_type","bundle_sha256"])
def test_result_correlation_rejects_other_input(bundle, field):
    result=result_for(bundle)
    setattr(result,field,"CLAIM" if field=="target_entity_type" else "other")
    with pytest.raises(InvalidComputeResult): service.validate_result(bundle,result)


@pytest.mark.parametrize("bad_layers", ["missing","wrong-key","wrong-number"])
def test_reject_incomplete_pipeline(bundle,bad_layers):
    result=result_for(bundle)
    if bad_layers=="missing": del result.layer_findings[6]
    elif bad_layers=="wrong-key": result.layer_findings[7]=result.layer_findings.pop(6)
    else: result.layer_findings[2].layer=3
    with pytest.raises(InvalidComputeResult): service.validate_result(bundle,result)


@pytest.mark.asyncio
async def test_single_use_job_rejects_replay_before_publish(bundle,monkeypatch):
    redis=AsyncMock(); redis.set.return_value=False
    monkeypatch.setattr(dispatcher,"get_redis_client",AsyncMock(return_value=redis))
    with pytest.raises(ComputeUnavailable,match="already"): await dispatcher.dispatch_compute_job(bundle)
    redis.lpush.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["redis","timeout","malformed","worker-timeout","cancelled"])
async def test_failure_never_yields_a_finding(bundle,monkeypatch,failure):
    dispatch=AsyncMock(return_value=bundle.job_id)
    fetch=AsyncMock(return_value=result_for(bundle))
    discard=AsyncMock()
    if failure=="redis": fetch.side_effect=RedisConnectionError("synthetic failure")
    if failure=="timeout": fetch.side_effect=TimeoutError()
    if failure=="malformed": fetch.return_value.job_id="replay"
    if failure=="worker-timeout": fetch.return_value.diagnostic_code="COMPUTE_TIMEOUT_EXCEEDED"
    if failure=="cancelled": fetch.side_effect=asyncio.CancelledError()
    monkeypatch.setattr(service,"dispatch_compute_job",dispatch)
    monkeypatch.setattr(service,"fetch_finding_result",fetch)
    monkeypatch.setattr(service,"discard_finding_result",discard)
    with pytest.raises(asyncio.CancelledError if failure=="cancelled" else ComputeUnavailable):
        async with service.compute_job(bundle): pytest.fail("must not reach DB persistence")
    discard.assert_awaited_once_with(bundle.job_id)


@pytest.mark.asyncio
async def test_result_is_retained_until_commit_and_cleaned_on_db_failure(bundle,monkeypatch):
    discard=AsyncMock()
    monkeypatch.setattr(service,"dispatch_compute_job",AsyncMock())
    monkeypatch.setattr(service,"fetch_finding_result",AsyncMock(return_value=result_for(bundle)))
    monkeypatch.setattr(service,"discard_finding_result",discard)
    with pytest.raises(RuntimeError,match="DB commit failed"):
        async with service.compute_job(bundle) as result:
            assert result.job_id==bundle.job_id
            discard.assert_not_awaited()
            raise RuntimeError("DB commit failed")
    discard.assert_awaited_once()


def test_backend_product_source_never_imports_worker():
    import ast
    root=Path(__file__).resolve().parents[2]/"app"
    for file in root.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node,ast.ImportFrom): assert not (node.module or "").startswith("worker")
            if isinstance(node,ast.Import): assert all(not item.name.startswith("worker") for item in node.names)


@pytest.mark.asyncio
async def test_cluster_without_node_transport_fails_instead_of_manufacturing_pass():
    from app.modules.cluster_orchestrator.dispatcher import ClusterTaskDispatcher
    from app.modules.cluster_orchestrator.registry import ClusterNodeRegistry
    from app.modules.cluster_orchestrator.wireguard import generate_wireguard_keypair
    from shared.schemas.cluster import NodeJoinRequest
    registry=ClusterNodeRegistry(cluster_secret="fixture")
    _,key=generate_wireguard_keypair()
    registry.register_node(NodeJoinRequest(hostname="fixture",wireguard_public_key=key,join_token="fixture"))
    dispatcher=ClusterTaskDispatcher(registry)
    bundle=JobBundle(job_id="fixture",version_id="v",target_entity_type="EQUATION",target_entity_id="e")
    with pytest.raises(RuntimeError,match="transport is not configured"):
        await dispatcher.dispatch_bundle(bundle)
    assert all(node.active_tasks==0 for node in registry.get_healthy_workers())


@pytest.mark.asyncio
async def test_persistence_refuses_to_synthesize_missing_layers(bundle):
    from datetime import datetime, timezone
    from app.modules.reality_constraint_engine.router import _persist_validation
    finding=result_for(bundle)
    finding.layer_findings=None
    db=Mock()
    with pytest.raises(InvalidComputeResult):
        await _persist_validation(db,bundle,finding,datetime.now(timezone.utc))
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_cluster_transport_result_checked_even_with_unused_mock_executor(bundle):
    from app.modules.cluster_orchestrator.dispatcher import ClusterTaskDispatcher
    from app.modules.cluster_orchestrator.registry import ClusterNodeRegistry
    from app.modules.cluster_orchestrator.wireguard import generate_wireguard_keypair
    from shared.schemas.cluster import NodeJoinRequest
    registry=ClusterNodeRegistry(cluster_secret='fixture')
    _,key=generate_wireguard_keypair()
    registry.register_node(NodeJoinRequest(hostname='fixture',wireguard_public_key=key,join_token='fixture'))
    invalid=result_for(bundle)
    invalid.version_id='other-version'
    transport=AsyncMock()
    transport.send_to_node.return_value=invalid.model_dump_json().encode()
    unused=Mock()
    dispatcher=ClusterTaskDispatcher(registry,transport=transport,mock_executor=unused)
    with pytest.raises(InvalidComputeResult):
        await dispatcher.dispatch_bundle(bundle)
    unused.assert_not_called()
    assert all(node.active_tasks==0 for node in registry.get_healthy_workers())

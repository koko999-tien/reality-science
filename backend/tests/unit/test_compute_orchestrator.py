import base64
import json
import pytest
from unittest.mock import AsyncMock, patch
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import ExprNode, NodeType, VariableSpec
from shared.schemas.finding_result import FindingResult, FindingState
from shared.models.enums import DiagnosticCode
from app.modules.compute_orchestrator.dispatcher import dispatch_compute_job
from app.modules.compute_orchestrator.ingestion import fetch_finding_result
from app.core.config import settings
from app.core.redis import get_redis_client, get_redis_result_client, close_redis_client


@pytest.mark.asyncio
async def test_dispatch_compute_job_formats_celery_envelope():
    mock_redis = AsyncMock()
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    bundle = JobBundle(
        job_id="test-job-uuid-1234",
        version_id="ver-1234",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-1234",
        expression_ast=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        variables=[var_x],
        units=[],
    )

    with patch("app.modules.compute_orchestrator.dispatcher.get_redis_client", return_value=mock_redis):
        dispatched_id = await dispatch_compute_job(bundle)
        assert dispatched_id == "test-job-uuid-1234"
        mock_redis.lpush.assert_called_once()
        queue_name, envelope_json = mock_redis.lpush.call_args[0]
        assert queue_name == "compute_tasks"

        envelope = json.loads(envelope_json)
        assert "headers" in envelope
        assert envelope["headers"]["task"] == "worker.tasks.verify_equation_ast"
        assert envelope["headers"]["id"] == "test-job-uuid-1234"
        assert envelope["properties"]["correlation_id"] == "test-job-uuid-1234"
        assert envelope["properties"]["body_encoding"] == "base64"

        # Decode body
        decoded_body = json.loads(base64.b64decode(envelope["body"]).decode("utf-8"))
        args = decoded_body[0]
        assert len(args) == 1
        assert args[0]["job_id"] == "test-job-uuid-1234"


@pytest.mark.asyncio
async def test_fetch_finding_result_reads_from_db1():
    mock_redis_result = AsyncMock()
    mock_result_data = {
        "status": "SUCCESS",
        "result": {
            "job_id": "test-job-uuid-1234",
            "state": "PASS",
            "diagnostic_code": "VALIDATION_PASSED",
            "message": "Passed",
            "dimensions_verified": True,
            "diagnostics": ["All ok"],
        },
    }
    mock_redis_result.get.return_value = json.dumps(mock_result_data)

    with patch("app.modules.compute_orchestrator.ingestion.get_redis_result_client", return_value=mock_redis_result):
        finding = await fetch_finding_result("test-job-uuid-1234")
        assert finding is not None
        assert finding.job_id == "test-job-uuid-1234"
        assert finding.state == FindingState.PASS
        assert finding.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
        mock_redis_result.get.assert_called_once_with("celery-task-meta-test-job-uuid-1234")


@pytest.mark.asyncio
async def test_fetch_finding_result_not_found():
    mock_redis_result = AsyncMock()
    mock_redis_result.get.return_value = None

    with patch("app.modules.compute_orchestrator.ingestion.get_redis_result_client", return_value=mock_redis_result):
        finding = await fetch_finding_result("non-existent")
        assert finding is None


def test_config_celery_result_backend_url():
    assert settings.celery_result_backend_url == "redis://:redis_secret_pw@localhost:6379/1"

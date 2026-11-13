import pytest
from pydantic import ValidationError
from shared.schemas.math_ast import ExprNode, NodeType, VariableSpec, UnitSpec
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.finding_result import FindingResult, FindingState


def test_job_bundle_creation():
    ast = ExprNode(node_type=NodeType.CONSTANT, value=42)
    bundle = JobBundle(
        job_id="job_001",
        version_id="ver_001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq_001",
        expression_ast=ast,
        variables=[],
        units=[],
        timeout_seconds=10,
    )
    assert bundle.job_id == "job_001"
    assert bundle.target_entity_type == TargetEntityType.EQUATION
    assert bundle.timeout_seconds == 10


def test_finding_result_creation():
    result = FindingResult(
        job_id="job_001",
        state=FindingState.PASS,
        diagnostic_code="VALIDATION_PASSED",
        message="AST simplified and dimensional units match.",
        symbolic_simplification="42",
        dimensions_verified=True,
        diagnostics=["Dimensions consistent"],
    )
    assert result.state == FindingState.PASS
    assert result.dimensions_verified is True

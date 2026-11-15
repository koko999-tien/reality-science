import pytest
from unittest.mock import patch
from celery.exceptions import SoftTimeLimitExceeded
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.models.enums import DiagnosticCode
from worker.tasks.compute_tasks import verify_equation_ast


def test_verify_equation_ast_success():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_t = VariableSpec(symbol="t", name="time", unit="second")

    # v * t -> [length]
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.MUL,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    bundle = JobBundle(
        job_id="job-001",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-001",
        expression_ast=node,
        variables=[var_v, var_t],
        units=[],
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.dimensions_verified is True
    assert "t*v" in res.symbolic_simplification or "v*t" in res.symbolic_simplification


def test_verify_equation_ast_layer1_undeclared_symbol():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    # x is undeclared
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="x"),
    )
    bundle = JobBundle(
        job_id="job-002",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-002",
        expression_ast=node,
        variables=[var_v],
        units=[],
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.UNDECLARED_SYMBOL.value
    assert res.dimensions_verified is False


def test_verify_equation_ast_layer2_singularity():
    # 1 / (x - 3) where x is real
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.SUB,
            left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
            right=ExprNode(node_type=NodeType.CONSTANT, value=3),
        ),
    )
    bundle = JobBundle(
        job_id="job-003",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-003",
        expression_ast=node,
        variables=[var_x],
        units=[],
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SINGULARITY_OR_DIVISION_BY_ZERO.value
    assert res.dimensions_verified is False


def test_verify_equation_ast_layer3_dimensional_mismatch():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_t = VariableSpec(symbol="t", name="time", unit="second")
    # v + t -> dimensional mismatch
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    bundle = JobBundle(
        job_id="job-004",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-004",
        expression_ast=node,
        variables=[var_v, var_t],
        units=[],
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.DIMENSIONAL_MISMATCH.value
    assert res.dimensions_verified is False


def test_verify_equation_ast_layer3_transcendental_dimensional_argument():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    # sin(x) where x has unit meter -> category error
    node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SIN,
        args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
    )
    bundle = JobBundle(
        job_id="job-005",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-005",
        expression_ast=node,
        variables=[var_x],
        units=[],
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.DIMENSIONED_TRANSCENDENTAL_ARGUMENT.value
    assert res.dimensions_verified is False


def test_verify_equation_ast_soft_time_limit():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    node = ExprNode(node_type=NodeType.VARIABLE, value="x")
    bundle = JobBundle(
        job_id="job-006",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-006",
        expression_ast=node,
        variables=[var_x],
        units=[],
    )

    with patch("worker.tasks.compute_tasks.validate_ast_semantics", side_effect=SoftTimeLimitExceeded()):
        result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
        res = FindingResult.model_validate(result_dict)
        assert res.state == FindingState.NEEDS_EXPERT_REVIEW
        assert res.diagnostic_code == DiagnosticCode.COMPUTE_TIMEOUT_EXCEEDED.value

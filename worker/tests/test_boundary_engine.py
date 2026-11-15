import pytest
import sympy as sp
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    VariableSpec,
)
from shared.schemas.finding_result import FindingState
from shared.models.enums import DiagnosticCode
from worker.core.boundary_engine import (
    analyze_boundary_and_singularities,
    check_singularities_and_poles,
    evaluate_boundary_limits,
    execute_richardson_stratified_sampling,
)


def test_pole_detection_in_real_domain():
    # 1 / (x - 2) with real domain -> pole at x = 2
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.SUB,
            left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
            right=ExprNode(node_type=NodeType.CONSTANT, value=2),
        ),
    )
    result = analyze_boundary_and_singularities(node, [var_x])
    assert result.is_valid is False
    assert result.state == FindingState.FAIL
    assert result.diagnostic_code == DiagnosticCode.SINGULARITY_OR_DIVISION_BY_ZERO.value
    assert any("x = 2" in s for s in result.singularities)


def test_pole_outside_positive_real_domain():
    # 1 / (x + 5) with positive_real domain -> root at x = -5 (outside domain)
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="positive_real")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.ADD,
            left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
            right=ExprNode(node_type=NodeType.CONSTANT, value=5),
        ),
    )
    result = analyze_boundary_and_singularities(node, [var_x])
    assert result.is_valid is True
    assert result.state == FindingState.PASS
    assert result.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value


def test_asymptotic_divergence_detection():
    # 1 / x as x -> 0+ diverges to oo
    var_x = VariableSpec(symbol="x", name="distance", unit="meter", domain="positive_real")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(node_type=NodeType.VARIABLE, value="x"),
    )
    # Pole check finds x = 0 is a pole in real, but for positive_real 0 is boundary!
    # Let's test evaluate_boundary_limits directly:
    x_sym = sp.Symbol("x", positive=True)
    expr = 1 / x_sym
    limits, divergences = evaluate_boundary_limits(expr, [var_x])
    assert "x -> 0+" in limits
    assert "oo" in limits["x -> 0+"]
    assert any("divergence" in d.lower() for d in divergences)


def test_richardson_numerical_fallback():
    # (sin(x)**2 + cos(x)**2) - 1 == 0
    # Even if symbolic simplification does or doesn't immediately zero out,
    # test execute_richardson_stratified_sampling directly:
    var_x = VariableSpec(symbol="x", name="angle", unit="radian", domain="real")
    x = sp.Symbol("x", real=True)
    # Constructed trigonometric identity difference
    diff = (sp.sin(x)**2 + sp.cos(x)**2) - 1
    is_equiv, max_err, logs = execute_richardson_stratified_sampling(diff, [var_x])
    assert is_equiv is True
    assert max_err < 1e-12

    # Now test an unprovable non-zero difference
    diff_fail = sp.sin(x) - 0.5
    is_equiv_fail, max_err_fail, _ = execute_richardson_stratified_sampling(diff_fail, [var_x])
    assert is_equiv_fail is False
    assert max_err_fail > 1e-5


def test_richardson_fallback_via_analyze_boundary():
    # Create an ExprNode representing (sin(x)**2 + cos(x)**2) - 1
    # When evaluated through analyze_boundary_and_singularities, it should either PASS or WARNING (Richardson)
    var_x = VariableSpec(symbol="x", name="angle", unit="dimensionless", domain="real")
    sin_sq = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.SIN,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        ),
        right=ExprNode(node_type=NodeType.CONSTANT, value=2),
    )
    cos_sq = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.COS,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        ),
        right=ExprNode(node_type=NodeType.CONSTANT, value=2),
    )
    lhs = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=sin_sq,
        right=cos_sq,
    )
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.SUB,
        left=lhs,
        right=ExprNode(node_type=NodeType.CONSTANT, value=1),
    )

    result = analyze_boundary_and_singularities(node, [var_x])
    assert result.is_valid is True
    assert result.state in (FindingState.PASS, FindingState.WARNING)

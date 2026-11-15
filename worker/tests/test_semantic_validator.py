import pytest
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)
from shared.models.enums import DiagnosticCode
from worker.core.semantic_validator import (
    validate_ast_semantics,
    extract_referenced_symbols,
    validate_variable_declarations,
)


def test_semantic_validator_valid_ast():
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    var_t = VariableSpec(symbol="t", name="time", unit="second", domain="positive_real")

    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )

    result = validate_ast_semantics(node, [var_x, var_t])
    assert result.is_valid is True
    assert result.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert result.referenced_symbols == {"x", "t"}


def test_semantic_validator_undeclared_symbol():
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    # y is not declared
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="y"),
    )

    result = validate_ast_semantics(node, [var_x])
    assert result.is_valid is False
    assert result.diagnostic_code == DiagnosticCode.UNDECLARED_SYMBOL.value
    assert "y" in result.message


def test_semantic_validator_complexity_gate_depth_exceeded():
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    # Build tree deeper than 15
    curr = ExprNode(node_type=NodeType.VARIABLE, value="x")
    for _ in range(16):
        curr = ExprNode(node_type=NodeType.UNARY_OP, op=OperatorType.NEG, left=curr)

    result = validate_ast_semantics(curr, [var_x])
    assert result.is_valid is False
    assert result.diagnostic_code == DiagnosticCode.COMPLEXITY_LIMIT_EXCEEDED.value
    assert "exceeds maximum limit of 15" in result.message


def test_semantic_validator_complexity_gate_power_exceeded():
    var_x = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value=25),
    )

    result = validate_ast_semantics(node, [var_x])
    assert result.is_valid is False
    assert result.diagnostic_code == DiagnosticCode.COMPLEXITY_LIMIT_EXCEEDED.value
    assert "exceeds maximum limit of 20" in result.message


def test_semantic_validator_conflicting_variable_declarations():
    var_x1 = VariableSpec(symbol="x", name="position", unit="meter", domain="real")
    var_x2 = VariableSpec(symbol="x", name="position", unit="second", domain="real")
    node = ExprNode(node_type=NodeType.VARIABLE, value="x")

    result = validate_ast_semantics(node, [var_x1, var_x2])
    assert result.is_valid is False
    assert "Conflicting duplicate" in result.message


def test_semantic_validator_extract_referenced_symbols_nested():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.SIN,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="theta")],
        ),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.VARIABLE, value="r"),
            right=ExprNode(node_type=NodeType.CONSTANT, value=2),
        ),
    )
    symbols = extract_referenced_symbols(node)
    assert symbols == {"theta", "r"}

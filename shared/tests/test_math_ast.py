import pytest
from pydantic import ValidationError
from shared.schemas.math_ast import (
    ExprNode,
    NodeType,
    OperatorType,
    AllowedFunction,
    UnitSpec,
    VariableSpec,
)


def test_unit_spec_valid():
    unit = UnitSpec(
        name="meter_per_second",
        symbol="m/s",
        dimensionality="[length] / [time]",
        scale_factor=1.0,
    )
    assert unit.symbol == "m/s"
    assert unit.dimensionality == "[length] / [time]"


def test_variable_spec_valid():
    var = VariableSpec(
        symbol="v_0",
        name="initial_velocity",
        unit="m/s",
        domain="real",
        latex_presentation="v_{0}",
    )
    assert var.symbol == "v_0"
    assert var.domain == "real"


def test_expr_node_binary_operation():
    left_node = ExprNode(node_type=NodeType.VARIABLE, value="x")
    right_node = ExprNode(node_type=NodeType.CONSTANT, value=2)
    add_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=left_node,
        right=right_node,
    )
    assert add_node.node_type == NodeType.BINARY_OP
    assert add_node.op == OperatorType.ADD
    assert add_node.left.value == "x"
    assert add_node.right.value == 2


def test_expr_node_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        ExprNode(
            node_type=NodeType.VARIABLE,
            value="x",
            malicious_field="injection",  # extra="forbid"
        )


def test_expr_node_rejects_booleans():
    with pytest.raises(ValidationError):
        ExprNode(node_type=NodeType.CONSTANT, value=True)
    with pytest.raises(ValidationError):
        ExprNode(node_type=NodeType.CONSTANT, value=False)


def test_expr_node_rejects_non_numeric_constant_string():
    with pytest.raises(ValidationError):
        ExprNode(node_type=NodeType.CONSTANT, value='__import__("os").system("echo RCE")')
    with pytest.raises(ValidationError):
        ExprNode(node_type=NodeType.CONSTANT, value="not_a_number")


def test_expr_node_accepts_numeric_constant_strings():
    n1 = ExprNode(node_type=NodeType.CONSTANT, value="42")
    assert n1.value == "42"
    n2 = ExprNode(node_type=NodeType.CONSTANT, value="-3.14159")
    assert n2.value == "-3.14159"
    n3 = ExprNode(node_type=NodeType.CONSTANT, value="1e-5")
    assert n3.value == "1e-5"

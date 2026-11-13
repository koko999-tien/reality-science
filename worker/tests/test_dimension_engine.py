import pytest
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType, VariableSpec, UnitSpec
from worker.core.dimension_engine import evaluate_ast_dimensions, DimensionalityCheckError


def test_consistent_dimensions():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_map = {"v": var_v}
    unit_map = {}

    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="v"),
    )
    quantity = evaluate_ast_dimensions(node, var_map, unit_map)
    assert str(quantity.dimensionality) == "[length] / [time]"


def test_dimensional_mismatch():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_t = VariableSpec(symbol="t", name="time", unit="second")
    var_map = {"v": var_v, "t": var_t}
    unit_map = {}

    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    with pytest.raises(DimensionalityCheckError):
        evaluate_ast_dimensions(node, var_map, unit_map)

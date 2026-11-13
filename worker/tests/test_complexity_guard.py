import pytest
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType
from worker.core.complexity_guard import (
    inspect_ast_complexity,
    ComplexityLimitExceededError,
)


def test_valid_complexity():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(node_type=NodeType.CONSTANT, value=2),
    )
    nodes, depth = inspect_ast_complexity(node)
    assert nodes == 3
    assert depth == 2


def test_exponential_bomb_rejected():
    bomb = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value=999),  # exceeds power limit 20
    )
    with pytest.raises(ComplexityLimitExceededError):
        inspect_ast_complexity(bomb)

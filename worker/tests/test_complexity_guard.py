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


def test_string_exponential_bomb_rejected():
    bomb = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="999"),  # string numeric literal
    )
    with pytest.raises(ComplexityLimitExceededError):
        inspect_ast_complexity(bomb)


def test_negative_exponential_bomb_rejected():
    bomb_num = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value=-25),
    )
    with pytest.raises(ComplexityLimitExceededError):
        inspect_ast_complexity(bomb_num)

    bomb_str = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="-25"),
    )
    with pytest.raises(ComplexityLimitExceededError):
        inspect_ast_complexity(bomb_str)


def test_compound_exponential_bomb_rejected():
    bomb = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.ADD,
            left=ExprNode(node_type=NodeType.CONSTANT, value=10),
            right=ExprNode(node_type=NodeType.CONSTANT, value=15),  # 10 + 15 = 25 > 20
        ),
    )
    with pytest.raises(ComplexityLimitExceededError):
        inspect_ast_complexity(bomb)


def test_compound_exponential_within_limit_accepted():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.ADD,
            left=ExprNode(node_type=NodeType.CONSTANT, value=2),
            right=ExprNode(node_type=NodeType.CONSTANT, value=3),  # 2 + 3 = 5 <= 20
        ),
    )
    nodes, depth = inspect_ast_complexity(node)
    assert nodes == 5
    assert depth == 3


def test_valid_string_exponent_accepted():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="3"),
    )
    nodes, depth = inspect_ast_complexity(node)
    assert nodes == 3
    assert depth == 2


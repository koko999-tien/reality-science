import pytest
import sympy as sp
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType, AllowedFunction
from worker.core.ast_evaluator import (
    ast_to_sympy,
    UndeclaredSymbolError,
    MathematicalSingularityError,
)


def test_ast_to_sympy_addition():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value=5),
    )
    expr = ast_to_sympy(node, declared_symbols={"x"})
    assert expr == sp.Symbol("x", real=True) + 5


def test_ast_to_sympy_undeclared_symbol():
    node = ExprNode(node_type=NodeType.VARIABLE, value="z")
    with pytest.raises(UndeclaredSymbolError):
        ast_to_sympy(node, declared_symbols={"x", "y"})


def test_ast_to_sympy_division_by_zero():
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        right=ExprNode(node_type=NodeType.CONSTANT, value=0),
    )
    with pytest.raises(MathematicalSingularityError):
        ast_to_sympy(node, declared_symbols=set())

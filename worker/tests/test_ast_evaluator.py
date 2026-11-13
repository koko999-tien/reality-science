import pytest
import sympy as sp
from pydantic import ValidationError
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType, AllowedFunction
from worker.core.ast_evaluator import (
    ast_to_sympy,
    safe_constant_to_sympy,
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


def test_ast_to_sympy_rejects_rce_string():
    """Verify arbitrary code execution strings are rejected and never executed."""
    # Via safe_constant_to_sympy directly
    with pytest.raises(ValueError):
        safe_constant_to_sympy('__import__("os").system("echo RCE_EXPLOITED")')

    # Via ExprNode validation
    with pytest.raises(ValidationError):
        ExprNode(
            node_type=NodeType.CONSTANT,
            value='__import__("os").system("echo RCE_EXPLOITED")',
        )


def test_ast_to_sympy_safe_numeric_parsing():
    """Verify numeric constants convert to sp.Integer / sp.Float without sympify."""
    e_int = ast_to_sympy(ExprNode(node_type=NodeType.CONSTANT, value=42), set())
    assert isinstance(e_int, sp.Integer) and e_int == 42

    e_float = ast_to_sympy(ExprNode(node_type=NodeType.CONSTANT, value=3.14), set())
    assert isinstance(e_float, sp.Float) and abs(float(e_float) - 3.14) < 1e-6

    e_str_int = ast_to_sympy(ExprNode(node_type=NodeType.CONSTANT, value="100"), set())
    assert isinstance(e_str_int, sp.Integer) and e_str_int == 100

    e_str_float = ast_to_sympy(ExprNode(node_type=NodeType.CONSTANT, value="-2.5e-2"), set())
    assert isinstance(e_str_float, sp.Float)


def test_ast_to_sympy_rejects_booleans():
    """Verify boolean values cannot be converted to mathematical numeric constants."""
    with pytest.raises(TypeError):
        safe_constant_to_sympy(True)
    with pytest.raises(TypeError):
        safe_constant_to_sympy(False)

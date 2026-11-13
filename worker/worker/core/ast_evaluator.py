import math
from typing import Dict, Set
import sympy as sp
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
)


class UndeclaredSymbolError(ValueError):
    pass


class MathematicalSingularityError(ValueError):
    pass


def safe_constant_to_sympy(val: object) -> sp.Expr:
    """Safely converts a constant value to a SymPy numeric expression without eval(), exec(), or sympify().

    Strictly supports int, float, or validated numeric strings.
    Rejects booleans, non-finite floats, and any non-numeric strings.
    """
    if val is None:
        raise ValueError("Constant node value cannot be None")
    if isinstance(val, bool):
        raise TypeError("Boolean values cannot be converted to mathematical numeric constants")

    if isinstance(val, int):
        return sp.Integer(val)

    if isinstance(val, float):
        if not math.isfinite(val):
            raise ValueError(f"Non-finite floating-point constant not permitted: {val}")
        return sp.Float(val)

    if isinstance(val, str):
        val_str = val.strip()
        try:
            if "." in val_str or "e" in val_str.lower():
                float_val = float(val_str)
                if not math.isfinite(float_val):
                    raise ValueError(f"Non-finite floating-point constant not permitted: {val}")
                return sp.Float(float_val)
            return sp.Integer(int(val_str))
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid constant numeric string: '{val}'. "
                "Arbitrary string expressions or code execution are forbidden by Decision 1."
            )

    raise TypeError(f"Unsupported constant type: {type(val).__name__}")


def ast_to_sympy(node: ExprNode, declared_symbols: Set[str]) -> sp.Expr:
    """Programmatically converts an ExprNode AST into a SymPy expression without eval(), exec(), or string sympify()."""
    if node.node_type == NodeType.CONSTANT:
        return safe_constant_to_sympy(node.value)

    if node.node_type == NodeType.VARIABLE:
        if not node.value or str(node.value) not in declared_symbols:
            raise UndeclaredSymbolError(f"Symbol '{node.value}' was not declared in variables list")
        return sp.Symbol(str(node.value), real=True)

    if node.node_type == NodeType.UNARY_OP:
        if not node.left:
            raise ValueError("Unary operation requires left operand")
        child_expr = ast_to_sympy(node.left, declared_symbols)
        if node.op == OperatorType.NEG:
            return -child_expr
        raise ValueError(f"Unsupported unary operator: {node.op}")

    if node.node_type == NodeType.BINARY_OP:
        if not node.left or not node.right:
            raise ValueError("Binary operation requires both left and right operands")
        left_expr = ast_to_sympy(node.left, declared_symbols)
        right_expr = ast_to_sympy(node.right, declared_symbols)

        if node.op == OperatorType.ADD:
            return left_expr + right_expr
        elif node.op == OperatorType.SUB:
            return left_expr - right_expr
        elif node.op == OperatorType.MUL:
            return left_expr * right_expr
        elif node.op == OperatorType.DIV:
            if right_expr == 0:
                raise MathematicalSingularityError("Division by zero in mathematical expression")
            return left_expr / right_expr
        elif node.op == OperatorType.POW:
            return left_expr ** right_expr
        raise ValueError(f"Unsupported binary operator: {node.op}")

    if node.node_type == NodeType.FUNCTION_CALL:
        if not node.args:
            raise ValueError("Function call requires arguments")
        arg_exprs = [ast_to_sympy(arg, declared_symbols) for arg in node.args]

        if node.func == AllowedFunction.SQRT:
            return sp.sqrt(arg_exprs[0])
        elif node.func == AllowedFunction.SIN:
            return sp.sin(arg_exprs[0])
        elif node.func == AllowedFunction.COS:
            return sp.cos(arg_exprs[0])
        elif node.func == AllowedFunction.EXP:
            return sp.exp(arg_exprs[0])
        elif node.func == AllowedFunction.LOG:
            return sp.log(arg_exprs[0])
        raise ValueError(f"Unsupported function call: {node.func}")

    raise ValueError(f"Unsupported node type: {node.node_type}")

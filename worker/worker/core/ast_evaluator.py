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


def ast_to_sympy(node: ExprNode, declared_symbols: Set[str]) -> sp.Expr:
    """Programmatically converts an ExprNode AST into a SymPy expression without eval() or exec()."""
    if node.node_type == NodeType.CONSTANT:
        if node.value is None:
            raise ValueError("Constant node value cannot be None")
        return sp.sympify(node.value)

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

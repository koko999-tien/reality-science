from typing import Dict, List
import pint
from shared.schemas.math_ast import (
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)

ureg = pint.UnitRegistry()


class DimensionalityCheckError(ValueError):
    pass


def evaluate_ast_dimensions(
    node: ExprNode,
    var_map: Dict[str, VariableSpec],
    unit_map: Dict[str, UnitSpec],
) -> pint.Quantity:
    """Recursively checks physical dimensional consistency of an ExprNode using Pint."""
    if node.node_type == NodeType.CONSTANT:
        return 1.0 * ureg.dimensionless

    if node.node_type == NodeType.VARIABLE:
        var_name = str(node.value)
        if var_name not in var_map:
            raise DimensionalityCheckError(f"Variable '{var_name}' not defined in variable specifications")
        unit_str = var_map[var_name].unit
        return 1.0 * ureg(unit_str)

    if node.node_type == NodeType.UNARY_OP:
        if not node.left:
            raise DimensionalityCheckError("Unary operator missing operand")
        return evaluate_ast_dimensions(node.left, var_map, unit_map)

    if node.node_type == NodeType.BINARY_OP:
        if not node.left or not node.right:
            raise DimensionalityCheckError("Binary operator missing operand")
        left_q = evaluate_ast_dimensions(node.left, var_map, unit_map)
        right_q = evaluate_ast_dimensions(node.right, var_map, unit_map)

        if node.op in (OperatorType.ADD, OperatorType.SUB):
            if left_q.dimensionality != right_q.dimensionality:
                raise DimensionalityCheckError(
                    f"Dimensional mismatch in addition/subtraction: {left_q.dimensionality} vs {right_q.dimensionality}"
                )
            return left_q

        if node.op == OperatorType.MUL:
            return left_q * right_q

        if node.op == OperatorType.DIV:
            return left_q / right_q

        if node.op == OperatorType.POW:
            # Exponent must be dimensionless
            if not right_q.dimensionless:
                raise DimensionalityCheckError(
                    f"Exponent must be dimensionless, got {right_q.dimensionality}"
                )
            power_val = float(node.right.value) if node.right.value is not None else 1.0
            return left_q ** power_val

    if node.node_type == NodeType.FUNCTION_CALL:
        # Transcendental functions (sin, cos, exp, log) require dimensionless argument
        if not node.args:
            raise DimensionalityCheckError("Function call requires arguments")
        arg_q = evaluate_ast_dimensions(node.args[0], var_map, unit_map)
        if not arg_q.dimensionless:
            raise DimensionalityCheckError(
                f"Transcendental function {node.func} requires dimensionless input, got {arg_q.dimensionality}"
            )
        return 1.0 * ureg.dimensionless

    raise DimensionalityCheckError(f"Unsupported node type: {node.node_type}")

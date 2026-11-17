from typing import Dict, List
import pint
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
    try_eval_constant_ast,
)

ureg = pint.UnitRegistry()


class DimensionalityCheckError(ValueError):
    pass


class TranscendentalDimensionalityError(DimensionalityCheckError):
    pass


def register_custom_unit(unit_spec: UnitSpec) -> None:
    """Dynamically registers custom UnitSpec from bundle.units via ureg.define()."""
    if unit_spec.name in ureg or unit_spec.symbol in ureg:
        return
    dim = unit_spec.dimensionality
    replacements = {
        "[length]": "meter",
        "[mass]": "kilogram",
        "[time]": "second",
        "[current]": "ampere",
        "[temperature]": "kelvin",
        "[substance]": "mole",
        "[luminosity]": "candela",
        "[dimensionless]": "1",
    }
    dim_expr = dim
    for k, v in replacements.items():
        dim_expr = dim_expr.replace(k, v)
    scale = unit_spec.scale_factor if unit_spec.scale_factor else 1.0
    def_str = f"{unit_spec.name} = {scale} * ({dim_expr}) = {unit_spec.symbol}"
    try:
        ureg.define(def_str)
    except Exception:
        pass


def evaluate_ast_dimensions(
    node: ExprNode,
    var_map: Dict[str, VariableSpec],
    unit_map: Dict[str, UnitSpec],
) -> pint.Quantity:
    """Recursively checks physical dimensional consistency of an ExprNode using Pint."""
    if unit_map:
        for u in unit_map.values():
            register_custom_unit(u)
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
            if left_q.dimensionless:
                return 1.0 * ureg.dimensionless

            exp_val = try_eval_constant_ast(node.right)
            if exp_val is None:
                raise DimensionalityCheckError(
                    f"Dimensionful base '{left_q.dimensionality}' requires a statically "
                    "evaluatable constant exponent to determine dimensional power"
                )
            return left_q ** exp_val

    if node.node_type == NodeType.FUNCTION_CALL:
        if not node.args or len(node.args) != 1:
            raise DimensionalityCheckError(
                f"Function {node.func} requires exactly 1 argument"
            )
        arg_q = evaluate_ast_dimensions(node.args[0], var_map, unit_map)

        if node.func == AllowedFunction.SQRT:
            return arg_q ** 0.5

        if node.func in (
            AllowedFunction.SIN,
            AllowedFunction.COS,
            AllowedFunction.EXP,
            AllowedFunction.LOG,
        ):
            if not arg_q.dimensionless:
                func_name = node.func.value if hasattr(node.func, "value") else str(node.func)
                raise TranscendentalDimensionalityError(
                    f"Transcendental function {func_name} requires dimensionless input, got {arg_q.dimensionality}"
                )
            return 1.0 * ureg.dimensionless

        raise DimensionalityCheckError(f"Unsupported function: {node.func}")

    raise DimensionalityCheckError(f"Unsupported node type: {node.node_type}")

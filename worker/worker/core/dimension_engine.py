from typing import Dict, List
import math
import re
from celery.exceptions import SoftTimeLimitExceeded
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


def register_custom_unit(unit_spec: UnitSpec, registry=None) -> None:
    """Dynamically registers custom UnitSpec from bundle.units via ureg.define()."""
    registry = registry if registry is not None else ureg
    dim = unit_spec.dimensionality
    # These fields describe one unit, never Pint's multi-definition/alias DSL.
    # Validate before either lookup or define, which both parse their input.
    if (not unit_spec.symbol or any(char.isspace() or ord(char) < 32 or ord(char) == 127
                                   for char in unit_spec.symbol)
            or re.search(r"[=;#@]", unit_spec.symbol)
            or not re.fullmatch(r"[A-Za-z0-9_\[\]*/().+\- \t]+", dim)):
        raise DimensionalityCheckError(f"Invalid custom unit syntax: {unit_spec.name}")
    scale = unit_spec.scale_factor
    if not math.isfinite(scale) or scale <= 0:
        raise DimensionalityCheckError(f"Invalid custom unit scale: {unit_spec.name}")
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
    def_str = f"{unit_spec.name} = {scale} * ({dim_expr}) = {unit_spec.symbol}"
    try:
        existing = [key in registry for key in (unit_spec.name, unit_spec.symbol)]
        if any(existing):
            # Built-in declarations may repeat the exact SI definition, but must
            # never shadow an alias, alter its scale or discard an offset.
            declared = (scale * registry(dim_expr)).to_base_units()
            if all(existing) and all(
                registry.Quantity(1, key).to_base_units() == declared
                and registry.Quantity(0, key).to_base_units().magnitude == 0
                for key in (unit_spec.name, unit_spec.symbol)
            ):
                return
            raise DimensionalityCheckError(f"Custom unit conflicts with an existing unit: {unit_spec.name}")
        registry.define(def_str)
    except SoftTimeLimitExceeded:
        raise
    except DimensionalityCheckError:
        raise
    except Exception as error:
        raise DimensionalityCheckError(f"Invalid custom unit: {unit_spec.name}") from error


def unit_registry(unit_map: Dict[str, UnitSpec]):
    registry = pint.UnitRegistry() if unit_map else ureg
    for unit in unit_map.values():
        register_custom_unit(unit, registry)
    return registry


def evaluate_ast_dimensions(
    node: ExprNode,
    var_map: Dict[str, VariableSpec],
    unit_map: Dict[str, UnitSpec],
    registry=None,
) -> pint.Quantity:
    """Recursively checks physical dimensional consistency of an ExprNode using Pint."""
    registry = registry if registry is not None else unit_registry(unit_map)
    return _evaluate_dimensions(node, var_map, unit_map, registry)


def _evaluate_dimensions(node, var_map, unit_map, registry):
    if node.node_type == NodeType.CONSTANT:
        return 1.0 * registry.dimensionless

    if node.node_type == NodeType.VARIABLE:
        var_name = str(node.value)
        if var_name not in var_map:
            raise DimensionalityCheckError(f"Variable '{var_name}' not defined in variable specifications")
        unit_str = var_map[var_name].unit
        return 1.0 * registry(unit_str)

    if node.node_type == NodeType.UNARY_OP:
        if not node.left:
            raise DimensionalityCheckError("Unary operator missing operand")
        return _evaluate_dimensions(node.left, var_map, unit_map, registry)

    if node.node_type == NodeType.BINARY_OP:
        if not node.left or not node.right:
            raise DimensionalityCheckError("Binary operator missing operand")
        left_q = _evaluate_dimensions(node.left, var_map, unit_map, registry)
        right_q = _evaluate_dimensions(node.right, var_map, unit_map, registry)

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
                return 1.0 * registry.dimensionless

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
        arg_q = _evaluate_dimensions(node.args[0], var_map, unit_map, registry)

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
            return 1.0 * registry.dimensionless

        raise DimensionalityCheckError(f"Unsupported function: {node.func}")

    raise DimensionalityCheckError(f"Unsupported node type: {node.node_type}")

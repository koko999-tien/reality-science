"""Layer 4 Physical Laws Invariants Evaluation Engine (Feature 24).

Enforces fundamental physical conservation laws and relativistic constraints:
1. Relativistic Speed of Light Invariant (v <= c, c = 299,792,458 m/s).
2. Conservation of Energy Invariant (Delta E = 0 in closed, isolated systems).
3. Conservation of Linear Momentum Invariant (Delta P = 0 in isolated systems without external force).
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import pint
from pydantic import ConfigDict
import sympy as sp

from shared.models.enums import DiagnosticCode
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    VariableSpec,
    try_eval_constant_ast,
)
from shared.schemas.physical_invariants import (
    PhysicalConstraintSpec,
    PhysicalConstraintType,
    PhysicalFindingDetails,
    SafetyPolicy,
    SystemContext,
)
from worker.core.ast_evaluator import (
    MathematicalSingularityError,
    UndeclaredSymbolError,
    ast_to_sympy,
)
from worker.core.dimension_engine import evaluate_ast_dimensions, ureg

# Fundamental physical constants
SPEED_OF_LIGHT_MS: float = 299792458.0
SPEED_OF_LIGHT_SQ: float = SPEED_OF_LIGHT_MS * SPEED_OF_LIGHT_MS

# Standard velocity, energy, and momentum dimensionality
VELOCITY_DIM = (ureg.meter / ureg.second).dimensionality
ENERGY_DIM = ureg.joule.dimensionality
MOMENTUM_DIM = (ureg.kilogram * ureg.meter / ureg.second).dimensionality

# Naming heuristics for delta expressions
ENERGY_DELTA_PATTERNS = re.compile(
    r"^(delta_?e|d_?e|e_?delta|delta_?energy|energy_?delta|energy_?change|delta_?u|d_?u)$",
    re.IGNORECASE,
)
MOMENTUM_DELTA_PATTERNS = re.compile(
    r"^(delta_?p|d_?p|p_?delta|delta_?momentum|momentum_?delta|momentum_?change)$",
    re.IGNORECASE,
)
VELOCITY_PATTERNS = re.compile(
    r"^(v|v_\d+|v_[xyz]|velocity|u|u_\d+|beta)$",
    re.IGNORECASE,
)


class PhysicalInvariantResult(FindingResult):
    """FindingResult extended with Layer 4 physical invariants metadata."""
    model_config = ConfigDict(extra="allow")

    is_valid: bool = True
    layer: int = 4
    details: Optional[Dict[str, Any]] = None


def is_velocity_unit(unit_str: str) -> bool:
    """Checks if a unit string has velocity dimensionality ([length] / [time])."""
    try:
        q = ureg(unit_str)
        return q.dimensionality == VELOCITY_DIM
    except Exception:
        return False


def to_si_velocity(val: float, unit_str: Optional[str]) -> Tuple[float, float]:
    """Converts a velocity quantity with a declared unit to SI m/s using Pint.

    Args:
        val: Numeric velocity value.
        unit_str: Declared unit string (e.g. 'meter / second', 'kilometer / second', 'mph', 'mm/s').

    Returns:
        Tuple of (val_in_ms, abs_val_in_ms).
        If unit_str is None, empty, dimensionless, or conversion fails,
        returns (val, abs(val)).
    """
    try:
        val_f = float(val)
    except (ValueError, TypeError):
        return 0.0, 0.0

    if not unit_str:
        return val_f, abs(val_f)
    try:
        q = ureg.Quantity(val_f, unit_str)
        if q.dimensionality == VELOCITY_DIM:
            si_val = float(q.to("meter / second").magnitude)
            return si_val, abs(si_val)
    except Exception:
        pass
    return val_f, abs(val_f)


def is_energy_unit(unit_str: str) -> bool:
    """Checks if a unit string has energy dimensionality ([mass] * [length]^2 / [time]^2)."""
    try:
        q = ureg(unit_str)
        return q.dimensionality == ENERGY_DIM
    except Exception:
        return False


def is_momentum_unit(unit_str: str) -> bool:
    """Checks if a unit string has momentum dimensionality ([mass] * [length] / [time])."""
    try:
        q = ureg(unit_str)
        return q.dimensionality == MOMENTUM_DIM
    except Exception:
        return False


def _check_speed_of_light(
    ast: ExprNode,
    variables: List[VariableSpec],
    sympy_expr: Optional[sp.Expr],
    system_context: SystemContext,
) -> Optional[PhysicalInvariantResult]:
    """Evaluates the relativistic speed of light invariant (v <= c, c = 299,792,458 m/s).

    Detects:
    1. Direct velocity quantities or numeric constants exceeding c (in any direction, |v| > c).
    2. Relativistic Lorentz factor terms (gamma = 1/sqrt(1 - v^2/c^2)) evaluated at v >= c.
    """
    var_map: Dict[str, VariableSpec] = {v.symbol: v for v in variables}
    velocity_vars: Set[str] = {
        v.symbol for v in variables
        if is_velocity_unit(v.unit) or VELOCITY_PATTERNS.match(v.symbol)
    }

    # Identify primary declared velocity unit
    default_velocity_unit: Optional[str] = None
    for sym in velocity_vars:
        spec = var_map.get(sym)
        if spec and spec.unit and is_velocity_unit(spec.unit):
            default_velocity_unit = spec.unit
            break
    if not default_velocity_unit and velocity_vars:
        first_spec = var_map.get(next(iter(velocity_vars)))
        if first_spec and first_spec.unit:
            default_velocity_unit = first_spec.unit

    # 1. Check if the entire AST or a constant velocity subtree evaluates to |v| > c
    # Check if the expression has velocity dimensionality
    try:
        ast_dim = evaluate_ast_dimensions(ast, var_map, {})
        has_velocity_dim = (ast_dim.dimensionality == VELOCITY_DIM)
    except Exception:
        has_velocity_dim = False

    ast_unit_str: Optional[str] = default_velocity_unit
    if has_velocity_dim:
        try:
            ast_unit_str = str(ast_dim.units)
        except Exception:
            pass

    const_val = try_eval_constant_ast(ast)
    if const_val is not None:
        if has_velocity_dim or (len(velocity_vars) > 0 and len(variables) == len(velocity_vars)):
            val_ms, abs_val_ms = to_si_velocity(const_val, ast_unit_str)
            if abs_val_ms > SPEED_OF_LIGHT_MS:
                excess_ms = float(abs_val_ms - SPEED_OF_LIGHT_MS)
                val_display = (
                    f"{val_ms:.2f} m/s"
                    if val_ms >= 0
                    else f"{val_ms:.2f} m/s (magnitude {abs_val_ms:.2f} m/s)"
                )
                diag_msg = (
                    f"Speed of light violation: {val_ms:.2f} m/s > {SPEED_OF_LIGHT_MS:.0f} m/s"
                    if val_ms >= 0
                    else f"Speed of light violation: {val_ms:.2f} m/s (|v| = {abs_val_ms:.2f} m/s) > {SPEED_OF_LIGHT_MS:.0f} m/s"
                )
                details = PhysicalFindingDetails(
                    invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                    violated_symbols=list(velocity_vars) or ["constant_velocity"],
                    calculated_value=float(val_ms),
                    limit_value=SPEED_OF_LIGHT_MS,
                    system_assumptions={"is_relativistic": system_context.is_relativistic},
                    details={
                        "excess_velocity_ms": excess_ms,
                        "speed_of_light_ms": SPEED_OF_LIGHT_MS,
                        "raw_value": float(const_val),
                        "raw_unit": ast_unit_str,
                    },
                )
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                    message=(
                        f"Relativistic speed of light invariant violated: velocity {val_display} "
                        f"exceeds c ({SPEED_OF_LIGHT_MS:.0f} m/s)."
                    ),
                    dimensions_verified=True,
                    is_valid=False,
                    details=details.model_dump(),
                    diagnostics=[
                        diag_msg,
                        f"Relativistic excess: {excess_ms:.2f} m/s",
                    ],
                )

    # 2. Check for constant nodes in velocity context exceeding c
    def _inspect_constant_nodes(
        node: ExprNode,
        parent_is_velocity: bool = False,
        parent_unit: Optional[str] = None,
    ) -> Optional[Tuple[float, float, float, Optional[str]]]:
        eff_unit = parent_unit or default_velocity_unit

        if parent_is_velocity or has_velocity_dim:
            if node.node_type == NodeType.CONSTANT and node.value is not None:
                try:
                    num_val = float(node.value)
                    val_ms, abs_val_ms = to_si_velocity(num_val, eff_unit)
                    if abs_val_ms > SPEED_OF_LIGHT_MS:
                        return (val_ms, abs_val_ms, num_val, eff_unit)
                except (ValueError, TypeError):
                    pass
            elif node.node_type == NodeType.UNARY_OP:
                val = try_eval_constant_ast(node)
                if val is not None:
                    val_ms, abs_val_ms = to_si_velocity(val, eff_unit)
                    if abs_val_ms > SPEED_OF_LIGHT_MS:
                        return (val_ms, abs_val_ms, val, eff_unit)

        if node.node_type == NodeType.BINARY_OP:
            # Check if operands involve velocity variables
            left_is_vel = False
            right_is_vel = False
            left_unit = parent_unit
            right_unit = parent_unit

            if node.left and node.left.node_type == NodeType.VARIABLE and str(node.left.value) in velocity_vars:
                left_is_vel = True
                spec = var_map.get(str(node.left.value))
                if spec and spec.unit:
                    left_unit = spec.unit
                    if node.op in (OperatorType.ADD, OperatorType.SUB):
                        right_unit = spec.unit
            if node.right and node.right.node_type == NodeType.VARIABLE and str(node.right.value) in velocity_vars:
                right_is_vel = True
                spec = var_map.get(str(node.right.value))
                if spec and spec.unit:
                    right_unit = spec.unit
                    if node.op in (OperatorType.ADD, OperatorType.SUB):
                        left_unit = spec.unit

            if node.left:
                res = _inspect_constant_nodes(
                    node.left,
                    parent_is_velocity=parent_is_velocity or right_is_vel,
                    parent_unit=left_unit or eff_unit,
                )
                if res is not None:
                    return res
            if node.right:
                res = _inspect_constant_nodes(
                    node.right,
                    parent_is_velocity=parent_is_velocity or left_is_vel,
                    parent_unit=right_unit or eff_unit,
                )
                if res is not None:
                    return res
        elif node.node_type == NodeType.UNARY_OP and node.left:
            return _inspect_constant_nodes(
                node.left,
                parent_is_velocity=parent_is_velocity,
                parent_unit=eff_unit,
            )
        elif node.node_type == NodeType.FUNCTION_CALL and node.args:
            for arg in node.args:
                res = _inspect_constant_nodes(
                    arg,
                    parent_is_velocity=parent_is_velocity,
                    parent_unit=eff_unit,
                )
                if res is not None:
                    return res
        return None

    exceeding_info = _inspect_constant_nodes(
        ast,
        parent_is_velocity=has_velocity_dim,
        parent_unit=ast_unit_str,
    )
    if exceeding_info is not None:
        val_ms, abs_val_ms, raw_val, eff_unit = exceeding_info
        excess_ms = float(abs_val_ms - SPEED_OF_LIGHT_MS)
        val_display = (
            f"{val_ms:.2f} m/s"
            if val_ms >= 0
            else f"{val_ms:.2f} m/s (magnitude {abs_val_ms:.2f} m/s)"
        )
        diag_str = (
            f"Speed of light violation: constant velocity {val_ms:.2f} m/s > {SPEED_OF_LIGHT_MS:.0f} m/s"
            if val_ms >= 0
            else f"Speed of light violation: constant velocity {val_ms:.2f} m/s (|v| = {abs_val_ms:.2f} m/s) > {SPEED_OF_LIGHT_MS:.0f} m/s"
        )
        details = PhysicalFindingDetails(
            invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
            violated_symbols=list(velocity_vars) or ["constant_velocity"],
            calculated_value=float(val_ms),
            limit_value=SPEED_OF_LIGHT_MS,
            system_assumptions={"is_relativistic": system_context.is_relativistic},
            details={
                "excess_velocity_ms": excess_ms,
                "speed_of_light_ms": SPEED_OF_LIGHT_MS,
                "raw_value": float(raw_val),
                "raw_unit": eff_unit,
            },
        )
        return PhysicalInvariantResult(
            job_id="physical_invariants",
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
            message=(
                f"Relativistic speed of light invariant violated: velocity constant {val_display} "
                f"exceeds c ({SPEED_OF_LIGHT_MS:.0f} m/s)."
            ),
            dimensions_verified=True,
            is_valid=False,
            details=details.model_dump(),
            diagnostics=[
                diag_str,
                f"Relativistic excess: {excess_ms:.2f} m/s",
            ],
        )

    # 3. Check AST for Lorentz factor / SQRT domain violations:
    def _inspect_ast_lorentz(node: ExprNode, in_denominator: bool = False) -> Optional[PhysicalInvariantResult]:
        if node.node_type == NodeType.FUNCTION_CALL and node.func == AllowedFunction.SQRT:
            if node.args and len(node.args) == 1:
                val = try_eval_constant_ast(node.args[0])
                if val is not None:
                    if val < 0:
                        details = PhysicalFindingDetails(
                            invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                            violated_symbols=list(velocity_vars) or ["radicand"],
                            calculated_value=float(val),
                            limit_value=0.0,
                            system_assumptions={"is_relativistic": system_context.is_relativistic},
                            details={"radicand": float(val), "reason": "imaginary_lorentz_factor"},
                        )
                        return PhysicalInvariantResult(
                            job_id="physical_invariants",
                            state=FindingState.FAIL,
                            diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                            message=(
                                f"Relativistic Lorentz factor domain violation: radicand 1 - v^2/c^2 = {val:.4e} < 0, "
                                "producing an unphysical imaginary Lorentz factor (superluminal velocity v > c)."
                            ),
                            dimensions_verified=True,
                            is_valid=False,
                            details=details.model_dump(),
                            diagnostics=[
                                f"Lorentz factor radicand < 0: {val:.4e}",
                                "Unphysical imaginary domain: superluminal velocity v > c",
                            ],
                        )
                    elif val == 0 and in_denominator:
                        details = PhysicalFindingDetails(
                            invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                            violated_symbols=list(velocity_vars) or ["radicand"],
                            calculated_value=0.0,
                            limit_value=0.0,
                            system_assumptions={"is_relativistic": system_context.is_relativistic},
                            details={"radicand": 0.0, "reason": "lorentz_singularity_at_c"},
                        )
                        return PhysicalInvariantResult(
                            job_id="physical_invariants",
                            state=FindingState.FAIL,
                            diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                            message=(
                                "Relativistic Lorentz factor singularity: 1 / sqrt(1 - v^2/c^2) evaluated at v = c "
                                "causes division by zero."
                            ),
                            dimensions_verified=True,
                            is_valid=False,
                            details=details.model_dump(),
                            diagnostics=[
                                "Lorentz factor singularity: division by zero at v = c",
                            ],
                        )
        elif node.node_type == NodeType.BINARY_OP:
            if node.op == OperatorType.DIV:
                if node.left:
                    res = _inspect_ast_lorentz(node.left, in_denominator=in_denominator)
                    if res is not None:
                        return res
                if node.right:
                    res = _inspect_ast_lorentz(node.right, in_denominator=True)
                    if res is not None:
                        return res
            else:
                if node.left:
                    res = _inspect_ast_lorentz(node.left, in_denominator=in_denominator)
                    if res is not None:
                        return res
                if node.right:
                    res = _inspect_ast_lorentz(node.right, in_denominator=in_denominator)
                    if res is not None:
                        return res
        elif node.node_type == NodeType.UNARY_OP and node.left:
            return _inspect_ast_lorentz(node.left, in_denominator=in_denominator)
        elif node.node_type == NodeType.FUNCTION_CALL and node.args:
            for arg in node.args:
                res = _inspect_ast_lorentz(arg, in_denominator=in_denominator)
                if res is not None:
                    return res
        return None

    lorentz_ast_res = _inspect_ast_lorentz(ast)
    if lorentz_ast_res is not None:
        return lorentz_ast_res

    # 4. Check for Lorentz factor terms in SymPy
    if sympy_expr is not None:
        if sympy_expr.has(sp.I) and (system_context.is_relativistic or len(velocity_vars) > 0):
            details = PhysicalFindingDetails(
                invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                violated_symbols=list(velocity_vars),
                calculated_value=None,
                limit_value=0.0,
                system_assumptions={"is_relativistic": system_context.is_relativistic},
                details={"reason": "imaginary_lorentz_factor"},
            )
            return PhysicalInvariantResult(
                job_id="physical_invariants",
                state=FindingState.FAIL,
                diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                message=(
                    "Relativistic Lorentz factor domain violation: expression contains imaginary component, "
                    "indicating superluminal velocity v > c."
                ),
                dimensions_verified=True,
                is_valid=False,
                details=details.model_dump(),
                diagnostics=[
                    "Expression contains imaginary unit I: superluminal velocity v > c",
                ],
            )
        for subexpr in sp.preorder_traversal(sympy_expr):
            # Check for powers with exponent 1/2 or -1/2 (sqrt in numerator or denominator)
            if isinstance(subexpr, sp.Pow):
                base, exp = subexpr.as_base_exp()
                is_half = (exp == sp.Rational(1, 2) or exp == 0.5)
                is_neg_half = (exp == -sp.Rational(1, 2) or exp == -0.5)

                if is_half or is_neg_half:
                    # Check if base is a number (numeric constant evaluation)
                    if base.is_number:
                        try:
                            val = float(base.evalf())
                            if val < 0:
                                details = PhysicalFindingDetails(
                                    invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                                    violated_symbols=list(velocity_vars),
                                    calculated_value=val,
                                    limit_value=0.0,
                                    system_assumptions={"is_relativistic": system_context.is_relativistic},
                                    details={"radicand": val, "reason": "imaginary_lorentz_factor"},
                                )
                                return PhysicalInvariantResult(
                                    job_id="physical_invariants",
                                    state=FindingState.FAIL,
                                    diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                                    message=(
                                        f"Relativistic Lorentz factor domain violation: radicand 1 - v^2/c^2 = {val:.4e} < 0, "
                                        "producing an unphysical imaginary Lorentz factor (superluminal velocity v > c)."
                                    ),
                                    dimensions_verified=True,
                                    is_valid=False,
                                    details=details.model_dump(),
                                    diagnostics=[
                                        f"Lorentz factor radicand < 0: {val:.4e}",
                                        "Unphysical imaginary domain: superluminal velocity v > c",
                                    ],
                                )
                            elif val == 0 and is_neg_half:
                                details = PhysicalFindingDetails(
                                    invariant_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
                                    violated_symbols=list(velocity_vars),
                                    calculated_value=val,
                                    limit_value=0.0,
                                    system_assumptions={"is_relativistic": system_context.is_relativistic},
                                    details={"radicand": 0.0, "reason": "lorentz_singularity_at_c"},
                                )
                                return PhysicalInvariantResult(
                                    job_id="physical_invariants",
                                    state=FindingState.FAIL,
                                    diagnostic_code=DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value,
                                    message=(
                                        "Relativistic Lorentz factor singularity: 1 / sqrt(1 - v^2/c^2) evaluated at v = c "
                                        "causes division by zero."
                                    ),
                                    dimensions_verified=True,
                                    is_valid=False,
                                    details=details.model_dump(),
                                    diagnostics=[
                                        "Lorentz factor singularity: division by zero at v = c",
                                    ],
                                )
                        except Exception:
                            pass

    return None


def _check_energy_conservation(
    ast: ExprNode,
    variables: List[VariableSpec],
    sympy_expr: Optional[sp.Expr],
    system_context: SystemContext,
) -> Optional[PhysicalInvariantResult]:
    """Evaluates Conservation of Energy Invariant (Delta E = 0).

    In closed systems (is_closed_system=True, has_external_heat_or_work=False):
    Delta E must be zero. If Delta E != 0:
    - strict_reject: returns FindingState.FAIL
    - permissive_flag: returns FindingState.WARNING

    In open systems (is_closed_system=False or has_external_heat_or_work=True):
    returns FindingState.NOT_APPLICABLE.
    """
    var_map: Dict[str, VariableSpec] = {v.symbol: v for v in variables}
    energy_vars: Set[str] = {
        v.symbol for v in variables if is_energy_unit(v.unit)
    }
    delta_energy_vars: Set[str] = {
        v.symbol for v in variables
        if ENERGY_DELTA_PATTERNS.match(v.symbol) or (is_energy_unit(v.unit) and "delta" in v.name.lower())
    }

    # Determine if expression represents an energy delta
    is_energy_delta = False
    if len(delta_energy_vars) > 0:
        is_energy_delta = True
    elif ast.node_type == NodeType.BINARY_OP and ast.op == OperatorType.SUB:
        # Check if left and right operands are energy quantities
        try:
            if ast.left and ast.right:
                dim_l = evaluate_ast_dimensions(ast.left, var_map, {})
                dim_r = evaluate_ast_dimensions(ast.right, var_map, {})
                if dim_l.dimensionality == ENERGY_DIM and dim_r.dimensionality == ENERGY_DIM:
                    is_energy_delta = True
        except Exception:
            pass

    if not is_energy_delta:
        return None

    # Evaluate energy balance symbolically
    if sympy_expr is None:
        return None

    simplified = sp.simplify(sympy_expr)

    # If the energy variation is provably 0
    if simplified == 0 or simplified == sp.Integer(0):
        return PhysicalInvariantResult(
            job_id="physical_invariants",
            state=FindingState.PASS,
            diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
            message="Conservation of energy verified: Delta E = 0.",
            dimensions_verified=True,
            is_valid=True,
            diagnostics=["Energy balance symbolically verified: Delta E = 0"],
        )

    # If simplified to a non-zero numerical constant
    if simplified.is_number and not simplified.free_symbols:
        delta_val = float(simplified.evalf())
        if abs(delta_val) > 1e-12:
            details = PhysicalFindingDetails(
                invariant_type=PhysicalConstraintType.ENERGY_CONSERVATION.value,
                violated_symbols=list(delta_energy_vars) or list(energy_vars) or ["delta_E"],
                calculated_value=delta_val,
                limit_value=0.0,
                system_assumptions={
                    "is_closed_system": system_context.is_closed_system,
                    "has_external_heat_or_work": system_context.has_external_heat_or_work,
                    "safety_policy": system_context.safety_policy,
                },
                details={
                    "delta_energy_joules": delta_val,
                    "simplified_expression": str(simplified),
                },
            )

            # Check open vs closed system
            if not system_context.is_closed_system or system_context.has_external_heat_or_work:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code=DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value,
                    message=(
                        f"Conservation of energy constraint is not applicable: open system or external heat/work declared "
                        f"(Delta E = {delta_val:.4e} J)."
                    ),
                    dimensions_verified=True,
                    is_valid=True,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Energy conservation not applicable for declared open system (Delta E = {delta_val:.4e} J)",
                    ],
                )

            # Closed system without external work or heat: violation
            if system_context.safety_policy == SafetyPolicy.PERMISSIVE_FLAG.value:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.WARNING,
                    diagnostic_code=DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value,
                    message=(
                        f"Conservation of energy warning: non-zero energy variation Delta E = {delta_val:.4e} J "
                        "in closed isolated system."
                    ),
                    dimensions_verified=True,
                    is_valid=True,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Permissive flag: non-zero Delta E = {delta_val:.4e} J in closed system",
                    ],
                )
            else:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value,
                    message=(
                        f"Conservation of energy violation: non-zero energy variation Delta E = {delta_val:.4e} J "
                        "in closed isolated system without external heat or work transfer."
                    ),
                    dimensions_verified=True,
                    is_valid=False,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Energy conservation violation: Delta E = {delta_val:.4e} J != 0",
                        "System context: closed system, zero external heat/work",
                    ],
                )

    return None


def _check_momentum_conservation(
    ast: ExprNode,
    variables: List[VariableSpec],
    sympy_expr: Optional[sp.Expr],
    system_context: SystemContext,
) -> Optional[PhysicalInvariantResult]:
    """Evaluates Conservation of Linear Momentum Invariant (Delta P = 0).

    In isolated systems without external force (has_external_forces=False):
    Delta P must be zero. If Delta P != 0:
    - strict_reject: returns FindingState.FAIL
    - permissive_flag: returns FindingState.WARNING

    When external forces are declared (has_external_forces=True):
    returns FindingState.NOT_APPLICABLE.
    """
    var_map: Dict[str, VariableSpec] = {v.symbol: v for v in variables}
    momentum_vars: Set[str] = {
        v.symbol for v in variables if is_momentum_unit(v.unit)
    }
    delta_momentum_vars: Set[str] = {
        v.symbol for v in variables
        if MOMENTUM_DELTA_PATTERNS.match(v.symbol) or (is_momentum_unit(v.unit) and "delta" in v.name.lower())
    }

    # Determine if expression represents a momentum delta
    is_momentum_delta = False
    if len(delta_momentum_vars) > 0:
        is_momentum_delta = True
    elif ast.node_type == NodeType.BINARY_OP and ast.op == OperatorType.SUB:
        try:
            if ast.left and ast.right:
                dim_l = evaluate_ast_dimensions(ast.left, var_map, {})
                dim_r = evaluate_ast_dimensions(ast.right, var_map, {})
                if dim_l.dimensionality == MOMENTUM_DIM and dim_r.dimensionality == MOMENTUM_DIM:
                    is_momentum_delta = True
        except Exception:
            pass

    if not is_momentum_delta:
        return None

    # Evaluate momentum balance symbolically
    if sympy_expr is None:
        return None

    simplified = sp.simplify(sympy_expr)

    # If the momentum variation is provably 0
    if simplified == 0 or simplified == sp.Integer(0):
        return PhysicalInvariantResult(
            job_id="physical_invariants",
            state=FindingState.PASS,
            diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
            message="Conservation of linear momentum verified: Delta P = 0.",
            dimensions_verified=True,
            is_valid=True,
            diagnostics=["Linear momentum balance symbolically verified: Delta P = 0"],
        )

    # If simplified to a non-zero numerical constant
    if simplified.is_number and not simplified.free_symbols:
        delta_val = float(simplified.evalf())
        if abs(delta_val) > 1e-12:
            details = PhysicalFindingDetails(
                invariant_type=PhysicalConstraintType.MOMENTUM_CONSERVATION.value,
                violated_symbols=list(delta_momentum_vars) or list(momentum_vars) or ["delta_P"],
                calculated_value=delta_val,
                limit_value=0.0,
                system_assumptions={
                    "is_closed_system": system_context.is_closed_system,
                    "has_external_forces": system_context.has_external_forces,
                    "safety_policy": system_context.safety_policy,
                },
                details={
                    "delta_momentum_kg_m_s": delta_val,
                    "simplified_expression": str(simplified),
                },
            )

            # When external forces are declared, conservation does not apply
            if system_context.has_external_forces:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code=DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value,
                    message=(
                        f"Conservation of linear momentum constraint is not applicable: external forces declared "
                        f"(Delta P = {delta_val:.4e} kg*m/s)."
                    ),
                    dimensions_verified=True,
                    is_valid=True,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Linear momentum conservation not applicable: external forces declared (Delta P = {delta_val:.4e} kg*m/s)",
                    ],
                )

            # Isolated system without external forces: violation
            if system_context.safety_policy == SafetyPolicy.PERMISSIVE_FLAG.value:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.WARNING,
                    diagnostic_code=DiagnosticCode.MOMENTUM_CONSERVATION_VIOLATION.value,
                    message=(
                        f"Conservation of linear momentum warning: non-zero momentum variation Delta P = {delta_val:.4e} kg*m/s "
                        "in isolated system without external forces."
                    ),
                    dimensions_verified=True,
                    is_valid=True,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Permissive flag: non-zero Delta P = {delta_val:.4e} kg*m/s in isolated system",
                    ],
                )
            else:
                return PhysicalInvariantResult(
                    job_id="physical_invariants",
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.MOMENTUM_CONSERVATION_VIOLATION.value,
                    message=(
                        f"Conservation of linear momentum violation: non-zero momentum variation Delta P = {delta_val:.4e} kg*m/s "
                        "in isolated system without external forces."
                    ),
                    dimensions_verified=True,
                    is_valid=False,
                    details=details.model_dump(),
                    diagnostics=[
                        f"Linear momentum conservation violation: Delta P = {delta_val:.4e} kg*m/s != 0",
                        "System context: isolated system, zero external forces",
                    ],
                )

    return None


def verify_physical_invariants(
    ast: ExprNode,
    variables: List[VariableSpec],
    system_context: Optional[SystemContext] = None,
) -> PhysicalInvariantResult:
    """Verifies physical law invariants (Layer 4) for a mathematical AST.

    Evaluates:
    - Speed of light invariant (v <= c)
    - Energy conservation (Delta E = 0 in closed systems)
    - Linear momentum conservation (Delta P = 0 in isolated systems)

    Returns a PhysicalInvariantResult (subclass of FindingResult).
    """
    ctx = system_context if system_context is not None else SystemContext()
    declared_symbols = {v.symbol for v in variables}

    # Safely convert to SymPy expression if possible
    sympy_expr: Optional[sp.Expr] = None
    try:
        sympy_expr = ast_to_sympy(ast, declared_symbols)
    except (UndeclaredSymbolError, MathematicalSingularityError, ValueError, TypeError):
        pass

    # 1. Evaluate Relativistic Speed of Light Invariant
    sol_res = _check_speed_of_light(ast, variables, sympy_expr, ctx)
    if sol_res is not None and not sol_res.is_valid:
        return sol_res

    # 2. Evaluate Conservation of Energy Invariant
    energy_res = _check_energy_conservation(ast, variables, sympy_expr, ctx)
    if energy_res is not None:
        if not energy_res.is_valid or energy_res.state in (FindingState.FAIL, FindingState.WARNING, FindingState.NOT_APPLICABLE):
            return energy_res

    # 3. Evaluate Conservation of Linear Momentum Invariant
    momentum_res = _check_momentum_conservation(ast, variables, sympy_expr, ctx)
    if momentum_res is not None:
        if not momentum_res.is_valid or momentum_res.state in (FindingState.FAIL, FindingState.WARNING, FindingState.NOT_APPLICABLE):
            return momentum_res

    # If any specific check passed with diagnostics
    diagnostics = ["Layer 4 Physical Invariants: OK (speed of light, energy, momentum verified)"]
    if sol_res and sol_res.diagnostics:
        diagnostics.extend(sol_res.diagnostics)
    if energy_res and energy_res.diagnostics:
        diagnostics.extend(energy_res.diagnostics)
    if momentum_res and momentum_res.diagnostics:
        diagnostics.extend(momentum_res.diagnostics)

    return PhysicalInvariantResult(
        job_id="physical_invariants",
        state=FindingState.PASS,
        diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
        message="Mathematical AST passed all Layer 4 physical law invariant constraints.",
        dimensions_verified=True,
        is_valid=True,
        diagnostics=diagnostics,
    )

import pytest
import math
from shared.models.enums import DiagnosticCode
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)
from shared.schemas.physical_invariants import (
    PhysicalConstraintSpec,
    PhysicalConstraintType,
    SafetyPolicy,
    SystemContext,
)
from worker.core.physical_invariants import (
    SPEED_OF_LIGHT_MS,
    PhysicalInvariantResult,
    verify_physical_invariants,
)
from worker.tasks.compute_tasks import verify_equation_ast


# ---------------------------------------------------------------------------
# Speed of Light Invariant Tests
# ---------------------------------------------------------------------------

def test_custom_velocity_scale_reaches_physical_checks_without_leaking():
    unit = UnitSpec(name="draft_velocity", symbol="draftvel", dimensionality="[length] / [time]", scale_factor=1000)
    bundle = JobBundle(job_id="custom-physical", version_id="v", target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="e", expression_ast=ExprNode(node_type=NodeType.CONSTANT, value=350000),
        variables=[VariableSpec(symbol="v", name="Velocity", unit=unit.name)], units=[unit], system_context=SystemContext())
    result = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    assert result["state"] == "FAIL" and result["diagnostic_code"] == "SPEED_OF_LIGHT_VIOLATION"
    assert result["layer_findings"][4]["details"]["calculated_value"] == 350000000
    # The same name in a subsequent job must use that job's scale.
    second = bundle.model_dump()
    second["units"][0]["scale_factor"] = 1
    assert verify_equation_ast.apply(args=[second]).get()["state"] == "PASS"
    from worker.core.dimension_engine import ureg
    assert unit.name not in ureg


def test_unknown_velocity_unit_returns_diagnostic_instead_of_assuming_si():
    result = verify_physical_invariants(ExprNode(node_type=NodeType.CONSTANT, value=350000),
        [VariableSpec(symbol="v", name="Velocity", unit="undefined_draft_velocity")])
    assert result.state != FindingState.PASS
    assert result.diagnostic_code == "DIMENSIONAL_MISMATCH"


@pytest.mark.parametrize("symbol", ["v", "u"])
@pytest.mark.parametrize("custom", [False, True])
def test_explicit_length_dimension_overrides_velocity_name_heuristic(symbol, custom):
    units = [UnitSpec(name="draft_length", symbol="dlen", dimensionality="[length]", scale_factor=1000)] if custom else []
    bundle = JobBundle(job_id="length-not-velocity", version_id="v", target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="e", expression_ast=ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.CONSTANT, value=2),
            right=ExprNode(node_type=NodeType.VARIABLE, value=symbol)),
        variables=[VariableSpec(symbol=symbol, name="Length", unit="draft_length" if custom else "meter")],
        units=units, system_context=SystemContext())
    result = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    assert result["state"] == "PASS"
    assert result["layer_findings"][4]["diagnostic_code"] != "DIMENSIONAL_MISMATCH"

def test_speed_of_light_subluminal_passes():
    """Velocity strictly below c must pass."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    # v = 2.0e8 m/s
    node = ExprNode(node_type=NodeType.CONSTANT, value="2.0e8")

    res = verify_physical_invariants(node, [var_v])
    assert isinstance(res, FindingResult)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_speed_of_light_exact_c_boundary_passes():
    """Exact speed of light c = 299792458 m/s must pass for physical limit."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value=str(int(SPEED_OF_LIGHT_MS)))

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_speed_of_light_boundary_plus_one_violation():
    """Velocity c + 1 m/s exceeds speed of light and must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    boundary_viol = str(int(SPEED_OF_LIGHT_MS) + 1)
    node = ExprNode(node_type=NodeType.CONSTANT, value=boundary_viol)

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert "exceeds c" in res.message


def test_speed_of_light_superluminal_constant_fails():
    """Velocity 3.5e8 m/s strictly exceeds c and must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="3.5e8")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert res.details is not None
    assert res.details["invariant_type"] == PhysicalConstraintType.SPEED_OF_LIGHT.value


def test_speed_of_light_in_ast_subexpression_fails():
    """Superluminal velocity constant in addition subexpression."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    # v + 3.2e8
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="3.2e8"),
    )

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False


def test_relativistic_lorentz_factor_subluminal_passes():
    """Lorentz factor gamma = 1 / sqrt(1 - (v/c)^2) with subluminal constant."""
    # (v / c)^2 = 0.64 (for v = 0.8c) => 1 - 0.64 = 0.36 => sqrt(0.36) = 0.6 => gamma = 1.6667
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    # 1 / sqrt(1 - 0.64)
    radicand_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.SUB,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=ExprNode(node_type=NodeType.CONSTANT, value=0.64),
    )
    sqrt_node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[radicand_node],
    )
    gamma_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=sqrt_node,
    )

    ctx = SystemContext(is_relativistic=True)
    res = verify_physical_invariants(gamma_node, [var_v], ctx)
    assert res.state == FindingState.PASS
    assert res.is_valid is True


def test_relativistic_lorentz_factor_superluminal_radicand_fails():
    """Lorentz factor with (v/c)^2 = 1.44 (v = 1.2c) gives 1 - 1.44 = -0.44 < 0."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    radicand_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.SUB,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=ExprNode(node_type=NodeType.CONSTANT, value=1.44),
    )
    sqrt_node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[radicand_node],
    )
    gamma_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=sqrt_node,
    )

    ctx = SystemContext(is_relativistic=True)
    res = verify_physical_invariants(gamma_node, [var_v], ctx)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert "imaginary" in res.message.lower() or "superluminal" in res.message.lower()


def test_relativistic_lorentz_factor_singularity_at_c_fails():
    """Lorentz factor at v = c gives 1 / sqrt(1 - 1) = 1 / sqrt(0) => division by zero."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    radicand_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.SUB,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
    )
    sqrt_node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[radicand_node],
    )
    gamma_node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.DIV,
        left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
        right=sqrt_node,
    )

    ctx = SystemContext(is_relativistic=True)
    res = verify_physical_invariants(gamma_node, [var_v], ctx)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False


# ---------------------------------------------------------------------------
# Energy Conservation Invariant Tests
# ---------------------------------------------------------------------------

def test_energy_conservation_zero_delta_passes():
    """Delta E = 0 in closed system passes conservation of energy."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    # delta_E = 0
    node = ExprNode(node_type=NodeType.CONSTANT, value=0.0)

    ctx = SystemContext(is_closed_system=True, has_external_heat_or_work=False)
    res = verify_physical_invariants(node, [var_de], ctx)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_energy_conservation_closed_system_violation_strict_reject():
    """Non-zero Delta E (e.g. 50 J) in closed isolated system fails with strict reject."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=50.0)

    ctx = SystemContext(
        is_closed_system=True,
        has_external_heat_or_work=False,
        safety_policy="strict_reject",
    )
    res = verify_physical_invariants(node, [var_de], ctx)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value
    assert res.is_valid is False
    assert "Delta E = 5.0000e+01 J" in res.message


def test_energy_conservation_closed_system_permissive_flag_warning():
    """Non-zero Delta E with permissive_flag returns WARNING instead of FAIL."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=50.0)

    ctx = SystemContext(
        is_closed_system=True,
        has_external_heat_or_work=False,
        safety_policy="permissive_flag",
    )
    res = verify_physical_invariants(node, [var_de], ctx)
    assert res.state == FindingState.WARNING
    assert res.diagnostic_code == DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value
    assert res.is_valid is True


def test_energy_conservation_open_system_not_applicable():
    """Open system (is_closed_system=False) yields NOT_APPLICABLE for Delta E != 0."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=50.0)

    ctx = SystemContext(
        is_closed_system=False,
        has_external_heat_or_work=False,
    )
    res = verify_physical_invariants(node, [var_de], ctx)
    assert res.state == FindingState.NOT_APPLICABLE
    assert res.diagnostic_code == DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value
    assert res.is_valid is True


def test_energy_conservation_external_work_not_applicable():
    """Closed system with declared external work/heat yields NOT_APPLICABLE for Delta E != 0."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=50.0)

    ctx = SystemContext(
        is_closed_system=True,
        has_external_heat_or_work=True,
    )
    res = verify_physical_invariants(node, [var_de], ctx)
    assert res.state == FindingState.NOT_APPLICABLE
    assert res.diagnostic_code == DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value
    assert res.is_valid is True


def test_energy_conservation_symbolic_cancellation():
    """Symbolic energy difference E - E = 0 passes."""
    var_e = VariableSpec(symbol="E", name="Energy", unit="joule")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.SUB,
        left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="E"),
    )

    ctx = SystemContext(is_closed_system=True, has_external_heat_or_work=False)
    res = verify_physical_invariants(node, [var_e], ctx)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value


# ---------------------------------------------------------------------------
# Linear Momentum Conservation Invariant Tests
# ---------------------------------------------------------------------------

def test_momentum_conservation_zero_delta_passes():
    """Delta P = 0 in isolated system passes linear momentum conservation."""
    var_dp = VariableSpec(symbol="delta_P", name="Momentum change", unit="kilogram * meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value=0.0)

    ctx = SystemContext(has_external_forces=False)
    res = verify_physical_invariants(node, [var_dp], ctx)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_momentum_conservation_isolated_system_violation_strict_reject():
    """Delta P = 15 kg*m/s in isolated system fails with MOMENTUM_CONSERVATION_VIOLATION."""
    var_dp = VariableSpec(symbol="delta_P", name="Momentum change", unit="kilogram * meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value=15.0)

    ctx = SystemContext(has_external_forces=False, safety_policy="strict_reject")
    res = verify_physical_invariants(node, [var_dp], ctx)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.MOMENTUM_CONSERVATION_VIOLATION.value
    assert res.is_valid is False
    assert "Delta P = 1.5000e+01 kg*m/s" in res.message


def test_momentum_conservation_isolated_system_permissive_flag_warning():
    """Delta P = 15 kg*m/s with permissive_flag returns WARNING."""
    var_dp = VariableSpec(symbol="delta_P", name="Momentum change", unit="kilogram * meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value=15.0)

    ctx = SystemContext(has_external_forces=False, safety_policy="permissive_flag")
    res = verify_physical_invariants(node, [var_dp], ctx)
    assert res.state == FindingState.WARNING
    assert res.diagnostic_code == DiagnosticCode.MOMENTUM_CONSERVATION_VIOLATION.value
    assert res.is_valid is True


def test_momentum_conservation_external_forces_not_applicable():
    """When external forces are declared, momentum conservation yields NOT_APPLICABLE."""
    var_dp = VariableSpec(symbol="delta_P", name="Momentum change", unit="kilogram * meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value=15.0)

    ctx = SystemContext(has_external_forces=True)
    res = verify_physical_invariants(node, [var_dp], ctx)
    assert res.state == FindingState.NOT_APPLICABLE
    assert res.diagnostic_code == DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value
    assert res.is_valid is True


# ---------------------------------------------------------------------------
# General Ordinary Physics Equations (Negative Control)
# ---------------------------------------------------------------------------

def test_ordinary_physics_equation_passes_all_invariants():
    """Ordinary physics expression without violations passes cleanly."""
    var_m = VariableSpec(symbol="m", name="mass", unit="kilogram")
    var_a = VariableSpec(symbol="a", name="acceleration", unit="meter / second ** 2")
    # F = m * a
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.MUL,
        left=ExprNode(node_type=NodeType.VARIABLE, value="m"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="a"),
    )

    res = verify_physical_invariants(node, [var_m, var_a])
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


# ---------------------------------------------------------------------------
# Celery Pipeline Integration Tests (verify_equation_ast)
# ---------------------------------------------------------------------------

def test_pipeline_integration_subluminal_equation_passes():
    """verify_equation_ast runs through all 4 layers and succeeds for valid subluminal equation."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_t = VariableSpec(symbol="t", name="time", unit="second")
    # v * t -> [length]
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.MUL,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    bundle = JobBundle(
        job_id="job-l4-pass",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-pass",
        expression_ast=node,
        variables=[var_v, var_t],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.dimensions_verified is True
    # Diagnostics must record Layer 1, Layer 2, Layer 3, and Layer 4
    diag_str = " ".join(res.diagnostics)
    assert "Layer 1 Syntax: OK" in diag_str
    assert "Layer 2 Boundary: OK" in diag_str
    assert "Layer 3 Dimension: OK" in diag_str
    assert "Layer 4 Physical Invariants: OK" in diag_str


def test_pipeline_integration_superluminal_velocity_fails():
    """verify_equation_ast rejects superluminal velocity at Layer 4."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    # 3.5e8 m/s
    node = ExprNode(node_type=NodeType.CONSTANT, value="3.5e8")
    bundle = JobBundle(
        job_id="job-l4-sol-fail",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-sol-fail",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert "Speed of light violation" in " ".join(res.diagnostics)


def test_pipeline_integration_closed_energy_violation_fails():
    """verify_equation_ast rejects non-zero Delta E in closed system at Layer 4."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=120.0)
    bundle = JobBundle(
        job_id="job-l4-energy-fail",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-energy-fail",
        expression_ast=node,
        variables=[var_de],
        units=[],
        system_context=SystemContext(is_closed_system=True, has_external_heat_or_work=False),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value
    assert "Energy conservation violation" in " ".join(res.diagnostics)


def test_pipeline_integration_open_energy_not_applicable():
    """verify_equation_ast returns NOT_APPLICABLE for Delta E in open system."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=120.0)
    bundle = JobBundle(
        job_id="job-l4-energy-na",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-energy-na",
        expression_ast=node,
        variables=[var_de],
        units=[],
        system_context=SystemContext(is_closed_system=False),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.NOT_APPLICABLE
    assert res.diagnostic_code == DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value


def test_pipeline_integration_permissive_flag_warning():
    """verify_equation_ast returns WARNING under permissive_flag policy."""
    var_de = VariableSpec(symbol="delta_E", name="Energy change", unit="joule")
    node = ExprNode(node_type=NodeType.CONSTANT, value=120.0)
    bundle = JobBundle(
        job_id="job-l4-warn",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-warn",
        expression_ast=node,
        variables=[var_de],
        units=[],
        system_context=SystemContext(is_closed_system=True, safety_policy="permissive_flag"),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.WARNING
    assert res.diagnostic_code == DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value


# ---------------------------------------------------------------------------
# Milestone 1 Iteration 2: Directional and Unit Invariance Tests
# ---------------------------------------------------------------------------

def test_speed_of_light_negative_superluminal_constant_fails():
    """Negative superluminal velocity v = -3.5e8 m/s (|v| > c) must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="-3.5e8")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert res.details is not None
    assert res.details["invariant_type"] == PhysicalConstraintType.SPEED_OF_LIGHT.value
    assert res.details["calculated_value"] == -350000000.0
    assert "exceeds c" in res.message


def test_speed_of_light_negative_two_c_fails():
    """Negative superluminal velocity v = -2c must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    neg_two_c = str(-2.0 * SPEED_OF_LIGHT_MS)
    node = ExprNode(node_type=NodeType.CONSTANT, value=neg_two_c)

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert "exceeds c" in res.message


def test_speed_of_light_negative_boundary_exact_passes():
    """Exact negative speed of light v = -c must pass."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    neg_c = str(-SPEED_OF_LIGHT_MS)
    node = ExprNode(node_type=NodeType.CONSTANT, value=neg_c)

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_speed_of_light_negative_boundary_minus_one_fails():
    """Velocity v = -(c + 1 m/s) exceeds c in magnitude and must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    neg_c_plus_one = str(-(SPEED_OF_LIGHT_MS + 1.0))
    node = ExprNode(node_type=NodeType.CONSTANT, value=neg_c_plus_one)

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert "exceeds c" in res.message


def test_speed_of_light_non_si_superluminal_kms_fails():
    """Non-SI velocity v = 350,000 km/s (= 3.5e8 m/s > c) must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="kilometer / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="350000")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert res.details is not None
    assert res.details["calculated_value"] == 350000000.0
    assert "exceeds c" in res.message


def test_speed_of_light_non_si_negative_superluminal_kms_fails():
    """Non-SI negative velocity v = -350,000 km/s (= -3.5e8 m/s) must fail."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="kilometer / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="-350000")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False
    assert "exceeds c" in res.message


def test_speed_of_light_non_si_subluminal_mms_passes():
    """Non-SI velocity v = 500,000,000 mm/s (= 500 km/s << c) must pass."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="millimeter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="500000000")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_speed_of_light_non_si_subluminal_mph_passes():
    """Non-SI velocity v = 500,000,000 mph (~ 2.235e8 m/s ~ 0.745c < c) must pass."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="mph")
    node = ExprNode(node_type=NodeType.CONSTANT, value="500000000")

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value
    assert res.is_valid is True


def test_speed_of_light_non_si_in_ast_subexpression_kms_fails():
    """Subexpression v + 350,000 with v in km/s must fail at Layer 4."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="kilometer / second")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="350000"),
    )

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert res.is_valid is False


def test_speed_of_light_non_si_in_ast_subexpression_mms_passes():
    """Subexpression v + 500,000,000 with v in mm/s must pass at Layer 4."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="millimeter / second")
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="500000000"),
    )

    res = verify_physical_invariants(node, [var_v])
    assert res.state == FindingState.PASS
    assert res.is_valid is True


def test_pipeline_integration_negative_superluminal_velocity_fails():
    """verify_equation_ast Celery pipeline rejects negative superluminal velocity."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="-3.5e8")
    bundle = JobBundle(
        job_id="job-l4-neg-sol-fail",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-neg-sol-fail",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value
    assert "Speed of light violation" in " ".join(res.diagnostics)


def test_pipeline_integration_non_si_superluminal_kms_fails():
    """verify_equation_ast Celery pipeline rejects v = 350,000 km/s."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="kilometer / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="350000")
    bundle = JobBundle(
        job_id="job-l4-kms-fail",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-kms-fail",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.FAIL
    assert res.diagnostic_code == DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value


def test_pipeline_integration_non_si_subluminal_mms_passes():
    """verify_equation_ast Celery pipeline passes v = 500,000,000 mm/s."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="millimeter / second")
    node = ExprNode(node_type=NodeType.CONSTANT, value="500000000")
    bundle = JobBundle(
        job_id="job-l4-mms-pass",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-mms-pass",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value


def test_pipeline_integration_non_si_subluminal_mph_passes():
    """verify_equation_ast Celery pipeline passes v = 500,000,000 mph."""
    var_v = VariableSpec(symbol="v", name="velocity", unit="mph")
    node = ExprNode(node_type=NodeType.CONSTANT, value="500000000")
    bundle = JobBundle(
        job_id="job-l4-mph-pass",
        version_id="ver-001",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-l4-mph-pass",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=SystemContext(),
    )

    result_dict = verify_equation_ast.apply(args=[bundle.model_dump()]).get()
    res = FindingResult.model_validate(result_dict)
    assert res.state == FindingState.PASS
    assert res.diagnostic_code == DiagnosticCode.VALIDATION_PASSED.value

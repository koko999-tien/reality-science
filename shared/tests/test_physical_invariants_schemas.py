import pytest
from pydantic import ValidationError

from shared.models.enums import DiagnosticCode
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import ExprNode, NodeType, VariableSpec
from shared.schemas.physical_invariants import (
    PhysicalConstraintSpec,
    PhysicalConstraintType,
    PhysicalFindingDetails,
    SafetyPolicy,
    SystemContext,
)


def test_diagnostic_code_physical_invariant_extensions():
    assert DiagnosticCode.PHYSICAL_INVARIANT_VIOLATION.value == "PHYSICAL_INVARIANT_VIOLATION"
    assert DiagnosticCode.ENERGY_CONSERVATION_VIOLATION.value == "ENERGY_CONSERVATION_VIOLATION"
    assert DiagnosticCode.MOMENTUM_CONSERVATION_VIOLATION.value == "MOMENTUM_CONSERVATION_VIOLATION"
    assert DiagnosticCode.SPEED_OF_LIGHT_VIOLATION.value == "SPEED_OF_LIGHT_VIOLATION"
    assert DiagnosticCode.PHYSICAL_CONSTRAINT_NOT_APPLICABLE.value == "PHYSICAL_CONSTRAINT_NOT_APPLICABLE"


def test_system_context_default_values():
    ctx = SystemContext()
    assert ctx.is_closed_system is True
    assert ctx.is_relativistic is False
    assert ctx.has_external_forces is False
    assert ctx.has_external_heat_or_work is False
    assert ctx.safety_policy == "strict_reject"
    assert ctx.assumptions == []


def test_system_context_custom_values():
    ctx = SystemContext(
        is_closed_system=False,
        is_relativistic=True,
        has_external_forces=True,
        has_external_heat_or_work=True,
        safety_policy="permissive_flag",
        assumptions=["open atmosphere boundary", "hypersonic regime"],
    )
    assert ctx.is_closed_system is False
    assert ctx.is_relativistic is True
    assert ctx.has_external_forces is True
    assert ctx.has_external_heat_or_work is True
    assert ctx.safety_policy == "permissive_flag"
    assert "open atmosphere boundary" in ctx.assumptions


def test_system_context_invalid_safety_policy():
    with pytest.raises(ValidationError):
        SystemContext(safety_policy="invalid_policy_name")


def test_system_context_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        SystemContext(arbitrary_extra_field="disallowed")


def test_physical_constraint_spec_creation():
    spec = PhysicalConstraintSpec(
        constraint_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
        name="Universal Speed Limit",
        description="Speed of light invariant v <= c",
        threshold=299792458.0,
        unit="meter / second",
        is_active=True,
    )
    assert spec.constraint_type == "SPEED_OF_LIGHT"
    assert spec.threshold == 299792458.0
    assert spec.is_active is True


def test_physical_constraint_spec_extra_forbidden():
    with pytest.raises(ValidationError):
        PhysicalConstraintSpec(
            constraint_type="SPEED_OF_LIGHT",
            name="Limit",
            unknown_arg="invalid",
        )


def test_physical_finding_details_creation():
    details = PhysicalFindingDetails(
        invariant_type=PhysicalConstraintType.ENERGY_CONSERVATION.value,
        violated_symbols=["delta_E"],
        calculated_value=42.0,
        limit_value=0.0,
        system_assumptions={"is_closed_system": True},
        details={"surplus_joules": 42.0},
    )
    assert details.invariant_type == "ENERGY_CONSERVATION"
    assert details.calculated_value == 42.0
    assert details.violated_symbols == ["delta_E"]
    assert details.system_assumptions["is_closed_system"] is True


def test_job_bundle_with_optional_system_context():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    node = ExprNode(node_type=NodeType.VARIABLE, value="v")

    # 1. JobBundle without system_context (defaults to None)
    bundle_none = JobBundle(
        job_id="job-none",
        version_id="ver-1",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-1",
        expression_ast=node,
        variables=[var_v],
        units=[],
    )
    assert bundle_none.system_context is None

    # 2. JobBundle with explicitly provided system_context
    ctx = SystemContext(is_closed_system=True, is_relativistic=True)
    bundle_with_ctx = JobBundle(
        job_id="job-ctx",
        version_id="ver-1",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-1",
        expression_ast=node,
        variables=[var_v],
        units=[],
        system_context=ctx,
    )
    assert bundle_with_ctx.system_context is not None
    assert bundle_with_ctx.system_context.is_closed_system is True
    assert bundle_with_ctx.system_context.is_relativistic is True

"""A Celery deadline must escape scientific fallbacks at the actual helper seam."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from celery.exceptions import SoftTimeLimitExceeded
import numpy as np
import pytest
import sympy as sp

from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.epistemic_logic import ClaimGraph, ClaimSpec
from shared.schemas.job_bundle import JobBundle
from shared.schemas.math_ast import ExprNode, UnitSpec, VariableSpec
from shared.schemas.physical_invariants import SystemContext
from worker.core import boundary_engine, dimension_engine, empirical_engine, epistemic_engine, physical_invariants
from worker.tasks.compute_tasks import verify_equation_ast


def bundle():
    return JobBundle(
        job_id="soft-deadline-job", version_id="soft-deadline-version",
        target_entity_type="EQUATION", target_entity_id="soft-deadline-equation",
        expression_ast=ExprNode(node_type="variable", value="x"),
        variables=[VariableSpec(symbol="x", name="position", unit="m")],
    )


@pytest.mark.parametrize("target", [
    "worker.tasks.dimensional.evaluate_ast_dimensions",
    "worker.core.boundary_engine.sp.limit",
    "worker.core.boundary_engine.ast_to_sympy",
])
def test_nested_deadline_is_operational_result_with_original_provenance(target):
    job = bundle()
    with patch(target, side_effect=SoftTimeLimitExceeded()) as operation:
        result = FindingResult.model_validate(verify_equation_ast.run(job.model_dump()))
    operation.assert_called()
    assert result.state == FindingState.NEEDS_EXPERT_REVIEW
    assert result.diagnostic_code == "COMPUTE_TIMEOUT_EXCEEDED"
    assert result.dimensions_verified is False
    assert result.job_id == job.job_id
    assert result.version_id == job.version_id
    assert result.target_entity_id == job.target_entity_id
    assert result.bundle_sha256 == job.fingerprint()


def test_denominator_extraction_does_not_swallow_deadline():
    expression = SimpleNamespace(as_numer_denom=Mock(side_effect=SoftTimeLimitExceeded()))
    with pytest.raises(SoftTimeLimitExceeded):
        boundary_engine.extract_denominators(expression)


def test_pole_solver_does_not_swallow_deadline():
    x = sp.Symbol("x")
    with patch.object(boundary_engine.sp, "solveset", side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            boundary_engine.check_singularities_and_poles(1 / (x + 1), bundle().variables)


@pytest.mark.parametrize("symbols", [set(), {sp.Symbol("x")}], ids=["constant", "sample"])
def test_sampling_does_not_turn_deadline_into_numerical_evidence(symbols):
    expression = SimpleNamespace(free_symbols=symbols, evalf=Mock(side_effect=SoftTimeLimitExceeded()))
    with pytest.raises(SoftTimeLimitExceeded):
        boundary_engine.execute_richardson_stratified_sampling(expression, bundle().variables)


def test_custom_unit_registration_does_not_swallow_deadline():
    unit = UnitSpec(name="deadline_unique_unit", symbol="deadline_unique_symbol",
                    dimensionality="[length]", scale_factor=2)
    with patch.object(dimension_engine.ureg, "define", side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            dimension_engine.register_custom_unit(unit)


@pytest.mark.parametrize("operation", [
    physical_invariants.is_velocity_unit,
    physical_invariants.is_energy_unit,
    physical_invariants.is_momentum_unit,
])
def test_unit_classification_does_not_turn_deadline_into_inapplicability(monkeypatch, operation):
    monkeypatch.setattr(physical_invariants, "ureg", Mock(side_effect=SoftTimeLimitExceeded()))
    with pytest.raises(SoftTimeLimitExceeded):
        operation("m/s")


def test_velocity_conversion_does_not_swallow_deadline(monkeypatch):
    registry = SimpleNamespace(Quantity=Mock(side_effect=SoftTimeLimitExceeded()))
    monkeypatch.setattr(physical_invariants, "ureg", registry)
    with pytest.raises(SoftTimeLimitExceeded):
        physical_invariants.to_si_velocity(1, "m/s")


def test_empirical_p_value_does_not_swallow_deadline():
    with patch.object(empirical_engine.mpmath, "gammainc", side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            empirical_engine.compute_empirical_metrics(np.array([1., 2.]), np.array([1., 2.]))


def test_empirical_evaluator_does_not_turn_deadline_into_invalid_ast():
    dataset = SimpleNamespace(independent_variable_symbol="x", to_xy_sigma=lambda: ([1, 2], [1, 2], [1, 1]))
    with patch.object(empirical_engine, "safe_evaluate_ast_numerical", side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            empirical_engine.correlate_empirical_data(bundle().expression_ast, bundle().variables, dataset)


def test_physical_dimension_inference_does_not_swallow_deadline():
    with patch.object(physical_invariants, "evaluate_ast_dimensions", side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            physical_invariants._check_speed_of_light(bundle().expression_ast, bundle().variables,
                                                      sp.Symbol("x"), SystemContext())


@pytest.mark.parametrize("kind", ["symbolic", "interval"])
def test_claim_comparison_does_not_turn_deadline_into_no_contradiction(kind):
    claims = [ClaimSpec(claim_id=str(i), claim_code=f"C{i}", claim_type="DERIVATION", statement="test",
                        target_variable="x", expression_ast=bundle().expression_ast if kind == "symbolic" else None,
                        metadata={"interval": [0, 1]} if kind == "interval" else {}) for i in range(2)]
    graph = ClaimGraph(graph_id="timeout-graph", version_id="v", claims=claims, variables=bundle().variables)
    target = "worker.core.epistemic_engine.ast_to_sympy" if kind == "symbolic" else "worker.core.epistemic_engine.sp.Interval"
    with patch(target, side_effect=SoftTimeLimitExceeded()):
        with pytest.raises(SoftTimeLimitExceeded):
            epistemic_engine.detect_contradictions(graph)

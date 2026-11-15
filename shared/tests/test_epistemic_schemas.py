import pytest
from pydantic import ValidationError

from shared.schemas.epistemic_logic import (
    ClaimType,
    RelationType,
    DependencyLogic,
    ContradictionType,
    ClaimSpec,
    ClaimDependency,
    CycleReport,
    ContradictionItem,
    ContradictionReport,
    EpistemicFinding,
    ClaimGraph,
    ClaimGraphValidationResult,
)
from shared.schemas.math_ast import ExprNode
from shared.schemas.finding_result import FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.models.enums import DiagnosticCode


def test_claim_spec_valid():
    claim = ClaimSpec(
        claim_id="clm-1",
        claim_code="CLM_001",
        claim_type=ClaimType.AXIOM,
        statement="Energy is conserved in an isolated system.",
        target_variable="E",
        local_state=FindingState.PASS,
        dependency_logic=DependencyLogic.ALL,
        confidence_score=1.0,
    )
    assert claim.claim_id == "clm-1"
    assert claim.claim_code == "CLM_001"
    assert claim.claim_type == ClaimType.AXIOM
    assert claim.local_state == FindingState.PASS

    # Test JSON serialization round-trip
    dumped = claim.model_dump()
    loaded = ClaimSpec.model_validate(dumped)
    assert loaded == claim


def test_claim_spec_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ClaimSpec(
            claim_id="clm-1",
            claim_code="CLM_001",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Valid statement text",
            unexpected_field="disallowed",
        )


def test_claim_dependency_validation():
    dep = ClaimDependency(
        source_claim_id="clm-2",
        target_claim_id="clm-1",
        relation_type=RelationType.DEPENDS_ON,
        justification="Derived from conservation law",
        weight=0.95,
    )
    assert dep.source_claim_id == "clm-2"
    assert dep.target_claim_id == "clm-1"
    assert dep.relation_type == RelationType.DEPENDS_ON
    assert dep.weight == 0.95

    # Weight boundary checks
    with pytest.raises(ValidationError):
        ClaimDependency(
            source_claim_id="clm-2",
            target_claim_id="clm-1",
            weight=1.5,
        )
    with pytest.raises(ValidationError):
        ClaimDependency(
            source_claim_id="clm-2",
            target_claim_id="clm-1",
            weight=-0.1,
        )


def test_cycle_report_schema():
    report = CycleReport(
        cycle_detected=True,
        cycles=[["clm-1", "clm-2", "clm-1"]],
        cyclic_claim_ids={"clm-1", "clm-2"},
    )
    assert report.cycle_detected is True
    assert len(report.cycles) == 1
    assert "clm-1" in report.cyclic_claim_ids

    dumped = report.model_dump()
    loaded = CycleReport.model_validate(dumped)
    assert loaded.cycle_detected is True
    assert loaded.cyclic_claim_ids == {"clm-1", "clm-2"}


def test_contradiction_report_schema():
    item = ContradictionItem(
        contradiction_type=ContradictionType.DIRECT_EQUALITY,
        claim_id_a="clm-1",
        claim_id_b="clm-2",
        conflict_variable="v",
        description="v = 3e8 conflicts with v = 2e8",
        symbolic_proof="Delta = 100000000.0 != 0",
        severity=FindingState.FAIL,
    )
    report = ContradictionReport(
        contradictions_found=True,
        items=[item],
    )
    assert report.contradictions_found is True
    assert len(report.items) == 1
    assert report.items[0].contradiction_type == ContradictionType.DIRECT_EQUALITY


def test_claim_graph_and_validation_result():
    claim1 = ClaimSpec(
        claim_id="clm-1",
        claim_code="CLM_001",
        claim_type=ClaimType.AXIOM,
        statement="Axiom 1",
    )
    claim2 = ClaimSpec(
        claim_id="clm-2",
        claim_code="CLM_002",
        claim_type=ClaimType.DERIVATION,
        statement="Derivation 1",
    )
    dep = ClaimDependency(
        source_claim_id="clm-2",
        target_claim_id="clm-1",
        relation_type=RelationType.DERIVED_FROM,
    )
    graph = ClaimGraph(
        graph_id="grp-1",
        version_id="ver-1",
        claims=[claim1, claim2],
        dependencies=[dep],
    )
    assert len(graph.claims) == 2
    assert len(graph.dependencies) == 1

    finding = EpistemicFinding(
        claim_id="clm-2",
        state=FindingState.PASS,
        diagnostic_code=DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value,
        message="All antecedent premises verified.",
    )
    result = ClaimGraphValidationResult(
        graph_id="grp-1",
        version_id="ver-1",
        overall_state=FindingState.PASS,
        cycle_report=CycleReport(cycle_detected=False),
        contradiction_report=ContradictionReport(contradictions_found=False),
        claim_findings={"clm-2": finding},
        topological_order=["clm-1", "clm-2"],
    )
    assert result.overall_state == FindingState.PASS
    assert result.topological_order == ["clm-1", "clm-2"]


def test_job_bundle_with_claim_graph():
    claim = ClaimSpec(
        claim_id="clm-1",
        claim_code="CLM_001",
        claim_type=ClaimType.AXIOM,
        statement="Standalone claim",
    )
    graph = ClaimGraph(
        graph_id="grp-1",
        version_id="ver-1",
        claims=[claim],
    )
    bundle = JobBundle(
        job_id="job-1",
        version_id="ver-1",
        target_entity_type=TargetEntityType.CLAIM,
        target_entity_id="grp-1",
        claim_graph=graph,
    )
    assert bundle.claim_graph is not None
    assert bundle.claim_graph.claims[0].claim_id == "clm-1"
    assert bundle.expression_ast is None

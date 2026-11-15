import ast
from pathlib import Path
import pytest
from pydantic import ValidationError

from shared.models.enums import DiagnosticCode
from shared.schemas.epistemic_logic import (
    ClaimDependency,
    ClaimGraph,
    ClaimSpec,
    ClaimType,
    ContradictionType,
    DependencyLogic,
    RelationType,
)
from shared.schemas.finding_result import FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType, VariableSpec
from worker.core.epistemic_engine import (
    detect_contradictions,
    detect_cycles,
    propagate_epistemic_status,
    verify_claim_graph,
)
from worker.tasks.compute_tasks import verify_equation_ast
from worker.tasks.epistemic import verify_epistemic_graph


# ==============================================================================
# 1. Cycle Detection (Tarjan's SCC + Cycle Extraction)
# ==============================================================================


def test_cycle_detection_self_loop():
    c1 = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.AXIOM, statement="Statement A")
    dep = ClaimDependency(source_claim_id="A", target_claim_id="A", relation_type=RelationType.DEPENDS_ON)
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1], dependencies=[dep])

    report = detect_cycles(graph)
    assert report.cycle_detected is True
    assert "A" in report.cyclic_claim_ids
    assert ["A", "A"] in report.cycles

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.FAIL
    assert res.claim_findings["A"].state == FindingState.FAIL
    assert res.claim_findings["A"].diagnostic_code == DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value


def test_cycle_detection_2_cycle():
    c1 = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.DERIVATION, statement="Statement A")
    c2 = ClaimSpec(claim_id="B", claim_code="CLM_B", claim_type=ClaimType.DERIVATION, statement="Statement B")
    # A depends on B, and B depends on A
    dep1 = ClaimDependency(source_claim_id="A", target_claim_id="B", relation_type=RelationType.DEPENDS_ON)
    dep2 = ClaimDependency(source_claim_id="B", target_claim_id="A", relation_type=RelationType.DEPENDS_ON)
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2], dependencies=[dep1, dep2])

    report = detect_cycles(graph)
    assert report.cycle_detected is True
    assert report.cyclic_claim_ids == {"A", "B"}
    assert len(report.cycles) == 1

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.FAIL
    assert res.claim_findings["A"].state == FindingState.FAIL
    assert res.claim_findings["B"].state == FindingState.FAIL
    assert res.claim_findings["A"].diagnostic_code == DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value


def test_cycle_detection_3_cycle_with_peripheral():
    c1 = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.DERIVATION, statement="Statement A")
    c2 = ClaimSpec(claim_id="B", claim_code="CLM_B", claim_type=ClaimType.DERIVATION, statement="Statement B")
    c3 = ClaimSpec(claim_id="C", claim_code="CLM_C", claim_type=ClaimType.DERIVATION, statement="Statement C")
    c4 = ClaimSpec(claim_id="D", claim_code="CLM_D", claim_type=ClaimType.DERIVATION, statement="Statement D")

    # A -> B -> C -> A (cycle) and D depends on C (peripheral)
    deps = [
        ClaimDependency(source_claim_id="A", target_claim_id="B", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="B", target_claim_id="C", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="C", target_claim_id="A", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="D", target_claim_id="C", relation_type=RelationType.DEPENDS_ON),
    ]
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2, c3, c4], dependencies=deps)

    report = detect_cycles(graph)
    assert report.cycle_detected is True
    assert report.cyclic_claim_ids == {"A", "B", "C"}
    assert "D" not in report.cyclic_claim_ids

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.FAIL
    assert res.claim_findings["A"].state == FindingState.FAIL
    assert res.claim_findings["B"].state == FindingState.FAIL
    assert res.claim_findings["C"].state == FindingState.FAIL
    # D is poisoned by C's failure
    assert res.claim_findings["D"].state == FindingState.FAIL
    assert res.claim_findings["D"].diagnostic_code == DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value


def test_valid_dag_diamond():
    # Diamond graph: Root A -> B, Root A -> C, B -> D, C -> D
    # Direction: D depends on B and C; B and C depend on A; A has no prerequisites.
    cA = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.AXIOM, statement="Axiom A", local_state=FindingState.PASS)
    cB = ClaimSpec(claim_id="B", claim_code="CLM_B", claim_type=ClaimType.DERIVATION, statement="Derivation B", local_state=FindingState.PASS)
    cC = ClaimSpec(claim_id="C", claim_code="CLM_C", claim_type=ClaimType.DERIVATION, statement="Derivation C", local_state=FindingState.PASS)
    cD = ClaimSpec(claim_id="D", claim_code="CLM_D", claim_type=ClaimType.DERIVATION, statement="Derivation D", local_state=FindingState.PASS)

    deps = [
        ClaimDependency(source_claim_id="B", target_claim_id="A", relation_type=RelationType.DERIVED_FROM),
        ClaimDependency(source_claim_id="C", target_claim_id="A", relation_type=RelationType.DERIVED_FROM),
        ClaimDependency(source_claim_id="D", target_claim_id="B", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="D", target_claim_id="C", relation_type=RelationType.DEPENDS_ON),
    ]
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[cA, cB, cC, cD], dependencies=deps)

    report = detect_cycles(graph)
    assert report.cycle_detected is False
    assert len(report.cyclic_claim_ids) == 0

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.PASS
    assert all(f.state == FindingState.PASS for f in res.claim_findings.values())


# ==============================================================================
# 2. Contradiction Engine (AST without eval/exec)
# ==============================================================================


def test_contradiction_direct_numerical_equality():
    # Claim 1: c_speed = 3.0e8
    # Claim 2: c_speed = 2.99792458e8
    ast1 = ExprNode(node_type=NodeType.CONSTANT, value=300000000.0)
    ast2 = ExprNode(node_type=NodeType.CONSTANT, value=299792458.0)

    c1 = ClaimSpec(
        claim_id="C1",
        claim_code="CLM_01",
        claim_type=ClaimType.AXIOM,
        statement="Speed of light is 3.0e8 m/s",
        target_variable="c",
        expression_ast=ast1,
        local_state=FindingState.PASS,
    )
    c2 = ClaimSpec(
        claim_id="C2",
        claim_code="CLM_02",
        claim_type=ClaimType.EMPIRICAL_OBSERVATION,
        statement="Speed of light is measured as 299792458 m/s",
        target_variable="c",
        expression_ast=ast2,
        local_state=FindingState.PASS,
    )
    var = VariableSpec(symbol="c", name="speed_of_light", unit="m/s")
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2], variables=[var])

    report = detect_contradictions(graph)
    assert report.contradictions_found is True
    assert len(report.items) == 1
    assert report.items[0].contradiction_type == ContradictionType.DIRECT_EQUALITY
    assert "Delta" in report.items[0].symbolic_proof

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.FAIL
    assert res.claim_findings["C1"].state == FindingState.FAIL
    assert res.claim_findings["C2"].state == FindingState.FAIL
    assert res.claim_findings["C1"].diagnostic_code == DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value


def test_contradiction_direct_symbolic_equality():
    # E = m * c^2 vs E = 0.5 * m * c^2
    var_m = VariableSpec(symbol="m", name="mass", unit="kg")
    var_c = VariableSpec(symbol="c", name="speed", unit="m/s")
    var_e = VariableSpec(symbol="E", name="energy", unit="J")

    # m * c^2
    c_squared = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.POW, left=ExprNode(node_type=NodeType.VARIABLE, value="c"), right=ExprNode(node_type=NodeType.CONSTANT, value=2))
    ast_einstein = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL, left=ExprNode(node_type=NodeType.VARIABLE, value="m"), right=c_squared)

    # 0.5 * m * c^2
    half_m = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL, left=ExprNode(node_type=NodeType.CONSTANT, value=0.5), right=ExprNode(node_type=NodeType.VARIABLE, value="m"))
    ast_half = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL, left=half_m, right=c_squared)

    c1 = ClaimSpec(claim_id="C1", claim_code="CLM_E1", claim_type=ClaimType.DERIVATION, statement="E = mc^2", target_variable="E", expression_ast=ast_einstein, local_state=FindingState.PASS)
    c2 = ClaimSpec(claim_id="C2", claim_code="CLM_E2", claim_type=ClaimType.DERIVATION, statement="E = 0.5 mc^2", target_variable="E", expression_ast=ast_half, local_state=FindingState.PASS)
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2], variables=[var_m, var_c, var_e])

    report = detect_contradictions(graph)
    assert report.contradictions_found is True
    assert report.items[0].contradiction_type == ContradictionType.DIRECT_EQUALITY


def test_non_contradiction_symbolic_equivalence():
    # E = m * c^2 vs E = c^2 * m (commutative equivalent)
    var_m = VariableSpec(symbol="m", name="mass", unit="kg")
    var_c = VariableSpec(symbol="c", name="speed", unit="m/s")
    var_e = VariableSpec(symbol="E", name="energy", unit="J")

    c_squared = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.POW, left=ExprNode(node_type=NodeType.VARIABLE, value="c"), right=ExprNode(node_type=NodeType.CONSTANT, value=2))
    ast1 = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL, left=ExprNode(node_type=NodeType.VARIABLE, value="m"), right=c_squared)
    ast2 = ExprNode(node_type=NodeType.BINARY_OP, op=OperatorType.MUL, left=c_squared, right=ExprNode(node_type=NodeType.VARIABLE, value="m"))

    c1 = ClaimSpec(claim_id="C1", claim_code="CLM_E1", claim_type=ClaimType.DERIVATION, statement="E = mc^2", target_variable="E", expression_ast=ast1, local_state=FindingState.PASS)
    c2 = ClaimSpec(claim_id="C2", claim_code="CLM_E2", claim_type=ClaimType.DERIVATION, statement="E = c^2 m", target_variable="E", expression_ast=ast2, local_state=FindingState.PASS)
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2], variables=[var_m, var_c, var_e])

    report = detect_contradictions(graph)
    assert report.contradictions_found is False


def test_contradiction_boundary_interval_conflict():
    # Claim 1: v in [0, 100]
    # Claim 2: v in [150, 200]
    c1 = ClaimSpec(
        claim_id="C1",
        claim_code="CLM_01",
        claim_type=ClaimType.DOMAIN_CONSTRAINT,
        statement="Subsonic speed",
        target_variable="v",
        metadata={"interval": [0, 100]},
        local_state=FindingState.PASS,
    )
    c2 = ClaimSpec(
        claim_id="C2",
        claim_code="CLM_02",
        claim_type=ClaimType.DOMAIN_CONSTRAINT,
        statement="Supersonic speed",
        target_variable="v",
        metadata={"interval": [150, 200]},
        local_state=FindingState.PASS,
    )
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2])
    report = detect_contradictions(graph)
    assert report.contradictions_found is True
    assert report.items[0].contradiction_type == ContradictionType.BOUNDARY_CONFLICT


def test_contradiction_sign_conflict():
    # Claim 1: Temperature is positive T > 0
    # Claim 2: Temperature is negative T <= 0
    c1 = ClaimSpec(
        claim_id="C1",
        claim_code="CLM_01",
        claim_type=ClaimType.DOMAIN_CONSTRAINT,
        statement="T is positive absolute temperature",
        target_variable="T",
        metadata={"sign": "positive"},
        local_state=FindingState.PASS,
    )
    c2 = ClaimSpec(
        claim_id="C2",
        claim_code="CLM_02",
        claim_type=ClaimType.DOMAIN_CONSTRAINT,
        statement="T is negative",
        target_variable="T",
        metadata={"sign": "negative"},
        local_state=FindingState.PASS,
    )
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2])
    report = detect_contradictions(graph)
    assert report.contradictions_found is True
    assert report.items[0].contradiction_type == ContradictionType.SIGN_CONFLICT


def test_contradiction_explicit_link():
    c1 = ClaimSpec(claim_id="C1", claim_code="CLM_01", claim_type=ClaimType.HYPOTHESIS, statement="Model A holds", local_state=FindingState.PASS)
    c2 = ClaimSpec(claim_id="C2", claim_code="CLM_02", claim_type=ClaimType.HYPOTHESIS, statement="Model B holds", local_state=FindingState.PASS)
    dep = ClaimDependency(source_claim_id="C1", target_claim_id="C2", relation_type=RelationType.CONTRADICTS)
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[c1, c2], dependencies=[dep])

    report = detect_contradictions(graph)
    assert report.contradictions_found is True
    assert report.items[0].contradiction_type == ContradictionType.EXPLICIT_CONTRADICTION


# ==============================================================================
# 3. Epistemic Status Propagation (Canonical 7-State Taxonomy)
# ==============================================================================


def test_epistemic_poisoning_forward_propagation():
    # Chain: A -> B -> C
    # A fails locally. B and C passed locally, but B depends on A, and C depends on B.
    cA = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.AXIOM, statement="Axiom A", local_state=FindingState.FAIL)
    cB = ClaimSpec(claim_id="B", claim_code="CLM_B", claim_type=ClaimType.DERIVATION, statement="Derivation B", local_state=FindingState.PASS)
    cC = ClaimSpec(claim_id="C", claim_code="CLM_C", claim_type=ClaimType.DERIVATION, statement="Derivation C", local_state=FindingState.PASS)

    deps = [
        ClaimDependency(source_claim_id="B", target_claim_id="A", relation_type=RelationType.DERIVED_FROM),
        ClaimDependency(source_claim_id="C", target_claim_id="B", relation_type=RelationType.DERIVED_FROM),
    ]
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[cA, cB, cC], dependencies=deps)

    res = verify_claim_graph(graph)
    assert res.overall_state == FindingState.FAIL
    assert res.claim_findings["A"].state == FindingState.FAIL
    assert res.claim_findings["B"].state == FindingState.FAIL
    assert res.claim_findings["B"].diagnostic_code == DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value
    assert res.claim_findings["C"].state == FindingState.FAIL
    assert res.claim_findings["C"].diagnostic_code == DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value


def test_conjunction_vs_disjunction_logic():
    # Conjunction (ALL): P1 (PASS), P2 (FAIL) -> C_ALL (FAIL)
    # Disjunction (ANY): P1 (PASS), P2 (FAIL) -> C_ANY (PASS)
    p1 = ClaimSpec(claim_id="P1", claim_code="CLM_P1", claim_type=ClaimType.AXIOM, statement="Premise 1", local_state=FindingState.PASS)
    p2 = ClaimSpec(claim_id="P2", claim_code="CLM_P2", claim_type=ClaimType.AXIOM, statement="Premise 2", local_state=FindingState.FAIL)

    c_all = ClaimSpec(
        claim_id="C_ALL",
        claim_code="CLM_ALL",
        claim_type=ClaimType.DERIVATION,
        statement="Requires both",
        local_state=FindingState.PASS,
        dependency_logic=DependencyLogic.ALL,
    )
    c_any = ClaimSpec(
        claim_id="C_ANY",
        claim_code="CLM_ANY",
        claim_type=ClaimType.DERIVATION,
        statement="Requires either",
        local_state=FindingState.PASS,
        dependency_logic=DependencyLogic.ANY,
    )

    deps = [
        ClaimDependency(source_claim_id="C_ALL", target_claim_id="P1", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="C_ALL", target_claim_id="P2", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="C_ANY", target_claim_id="P1", relation_type=RelationType.DEPENDS_ON),
        ClaimDependency(source_claim_id="C_ANY", target_claim_id="P2", relation_type=RelationType.DEPENDS_ON),
    ]
    graph = ClaimGraph(graph_id="g1", version_id="v1", claims=[p1, p2, c_all, c_any], dependencies=deps)

    res = verify_claim_graph(graph)
    assert res.claim_findings["C_ALL"].state == FindingState.FAIL
    assert res.claim_findings["C_ALL"].diagnostic_code == DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value
    assert res.claim_findings["C_ANY"].state == FindingState.PASS
    assert res.claim_findings["C_ANY"].diagnostic_code == DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value


def test_warning_and_uncertainty_inheritance():
    # Antecedent with WARNING inherits WARNING
    p_warn = ClaimSpec(claim_id="P1", claim_code="CLM_P1", claim_type=ClaimType.AXIOM, statement="Premise 1", local_state=FindingState.WARNING)
    c_dep = ClaimSpec(claim_id="C1", claim_code="CLM_C1", claim_type=ClaimType.DERIVATION, statement="Claim 1", local_state=FindingState.PASS)
    dep1 = ClaimDependency(source_claim_id="C1", target_claim_id="P1", relation_type=RelationType.DEPENDS_ON)

    graph1 = ClaimGraph(graph_id="g1", version_id="v1", claims=[p_warn, c_dep], dependencies=[dep1])
    res1 = verify_claim_graph(graph1)
    assert res1.claim_findings["C1"].state == FindingState.WARNING
    assert res1.claim_findings["C1"].diagnostic_code == DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value

    # Antecedent with NOT_YET_TESTED inherits INSUFFICIENT_DATA
    p_untested = ClaimSpec(claim_id="P2", claim_code="CLM_P2", claim_type=ClaimType.AXIOM, statement="Premise 2", local_state=FindingState.NOT_YET_TESTED)
    c_dep2 = ClaimSpec(claim_id="C2", claim_code="CLM_C2", claim_type=ClaimType.DERIVATION, statement="Claim 2", local_state=FindingState.PASS)
    dep2 = ClaimDependency(source_claim_id="C2", target_claim_id="P2", relation_type=RelationType.DEPENDS_ON)

    graph2 = ClaimGraph(graph_id="g2", version_id="v2", claims=[p_untested, c_dep2], dependencies=[dep2])
    res2 = verify_claim_graph(graph2)
    assert res2.claim_findings["C2"].state == FindingState.INSUFFICIENT_DATA
    assert res2.claim_findings["C2"].diagnostic_code == DiagnosticCode.EPISTEMIC_DEPENDENCY_UNRESOLVED.value


# ==============================================================================
# 4. Celery Task Execution in Zone 3 Compute Worker
# ==============================================================================


def test_verify_epistemic_graph_celery_task():
    cA = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.AXIOM, statement="Axiom A", local_state=FindingState.PASS)
    cB = ClaimSpec(claim_id="B", claim_code="CLM_B", claim_type=ClaimType.DERIVATION, statement="Derivation B", local_state=FindingState.PASS)
    dep = ClaimDependency(source_claim_id="B", target_claim_id="A", relation_type=RelationType.DEPENDS_ON)
    graph = ClaimGraph(graph_id="grp-100", version_id="ver-100", claims=[cA, cB], dependencies=[dep])

    result_dict = verify_epistemic_graph(graph.model_dump())
    assert result_dict["job_id"] == "grp-100"
    assert result_dict["state"] == FindingState.PASS.value
    assert result_dict["layer"] == 6
    assert result_dict["dimensions_verified"] is True


def test_verify_equation_ast_with_claim_graph():
    # Pass JobBundle with target_entity_type == CLAIM and claim_graph
    cA = ClaimSpec(claim_id="A", claim_code="CLM_A", claim_type=ClaimType.AXIOM, statement="Axiom A", local_state=FindingState.PASS)
    graph = ClaimGraph(graph_id="grp-200", version_id="ver-200", claims=[cA])

    bundle = JobBundle(
        job_id="job-claim-1",
        version_id="ver-200",
        target_entity_type=TargetEntityType.CLAIM,
        target_entity_id="grp-200",
        claim_graph=graph,
    )
    result_dict = verify_equation_ast(bundle.model_dump())
    assert result_dict["job_id"] == "job-claim-1"
    assert result_dict["state"] == FindingState.PASS.value
    assert result_dict["layer"] == 6


# ==============================================================================
# 5. Zone 3 Anti-Database Isolation Audit
# ==============================================================================


def test_epistemic_engine_zero_database_imports():
    """Confirms epistemic_engine.py has ZERO SQL/ORM/database imports."""
    engine_file = Path("D:/Reality_Science/worker/worker/core/epistemic_engine.py")
    assert engine_file.exists(), "epistemic_engine.py must exist"

    tree = ast.parse(engine_file.read_text(encoding="utf-8"))
    forbidden = {"sqlalchemy", "sqlite3", "psycopg", "asyncpg", "databases", "ormar", "tortoise", "peewee", "sqlmodel"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                assert root_module not in forbidden, f"Forbidden database import in epistemic engine: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                assert root_module not in forbidden, f"Forbidden database import in epistemic engine: {node.module}"

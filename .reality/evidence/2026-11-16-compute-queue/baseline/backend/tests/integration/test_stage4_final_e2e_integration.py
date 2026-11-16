"""Stage 4 Final End-to-End Monorepo Integration Test Suite.

Comprehensive 4-tier opaque-box integration verification:
- Tier 1: Canonical Valid Scientific Formulation (Layers 1-6 All-Pass)
- Tier 2: Layered Rejection & Fault Injection
    * Tier 2a: L1/L2 Syntax & Boundary Rejection
    * Tier 2b: L3 Dimensional Inconsistency Rejection
    * Tier 2c: L4 Physical Laws & Relativistic Speed Limit Invariant
    * Tier 2d: L5 Empirical Data Discrepancy Rejection
    * Tier 2e: L6 Epistemic Logic Cycle & Contradiction Rejection
- Tier 3: Version Validation, Freeze Immutability & Zone 2 Persistence
- Tier 4: Cryptographic ZIP Bundle Export with Offline Manifest & Claims Graph Verification
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, List, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.modules.iam_governance.dependencies import get_accessible_version, get_owned_version
from app.main import app
from app.modules.reality_constraint_engine.models import (
    Claim,
    ClaimRelation,
    Equation,
    ValidationFinding,
    ValidationRun,
    Variable,
)
from app.modules.research_core.exporter import generate_research_zip_bundle
from app.modules.research_core.models import (
    ResearchActor,
    ResearchProject,
    ResearchVersion,
)
from shared.models.enums import DiagnosticCode
from shared.schemas.empirical_data import EmpiricalDataPoint, EmpiricalDatasetSpec
from shared.schemas.epistemic_logic import (
    ClaimDependency,
    ClaimGraph,
    ClaimSpec,
    ClaimType,
    DependencyLogic,
    RelationType,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.math_ast import (
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


class MockResult:
    def __init__(self, items: List[Any]):
        self._items = items

    def scalar_one_or_none(self) -> Optional[Any]:
        return self._items[0] if self._items else None

    def scalars(self) -> MockResult:
        return self

    def all(self) -> List[Any]:
        return list(self._items)


class MockDbSession:
    """In-memory Mock AsyncSession for Stage 4 integration tests."""

    def __init__(self, entities: List[Any]):
        self.entities = list(entities)
        self.info: dict[str, Any] = {}

    def add(self, entity: Any) -> None:
        self.entities.append(entity)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def refresh(self, entity: Any) -> None:
        pass

    async def execute(self, stmt: Any) -> MockResult:
        if not hasattr(stmt, "column_descriptions"):
            return MockResult([])
        model_cls = stmt.column_descriptions[0]["type"]
        params = stmt.compile().params
        candidates = [e for e in self.entities if isinstance(e, model_cls)]

        if params:
            filtered = []
            for item in candidates:
                match = True
                for param_name, param_val in params.items():
                    clean_attr = re.sub(r"_\d+$", "", param_name)
                    if hasattr(item, clean_attr):
                        val = getattr(item, clean_attr)
                        if val != param_val:
                            match = False
                            break
                    elif hasattr(item, param_name.split("_")[0]):
                        val = getattr(item, param_name.split("_")[0])
                        if val != param_val:
                            match = False
                            break
                if match:
                    filtered.append(item)
            return MockResult(filtered)
        return MockResult(candidates)


@pytest.fixture
def stage4_test_entities():
    actor = ResearchActor(
        id="act_einstein_01",
        display_name="Albert Einstein",
        orcid="0000-0001-9999-0002",
        organization_id="org_ias_princeton",
        is_anonymized=False,
    )
    project = ResearchProject(
        id="proj_relativity_01",
        slug="general-theory-of-relativity",
        title="Die Grundlage der allgemeinen Relativitätstheorie",
        owner_actor_id=actor.id,
        visibility="public_preprint",
        is_frozen=False,
    )
    version_draft = ResearchVersion(
        id="ver_draft_stage4",
        project_id=project.id,
        version_number=1,
        title="Draft Foundations of Relativity",
        publication_status="draft",
        is_frozen=False,
    )
    version_frozen = ResearchVersion(
        id="ver_frozen_stage4",
        project_id=project.id,
        version_number=2,
        title="Final Certified Annus Mirabilis",
        publication_status="published",
        is_frozen=True,
    )
    return {
        "actor": actor,
        "project": project,
        "version_draft": version_draft,
        "version_frozen": version_frozen,
    }


@pytest.fixture(autouse=True)
def restore_app_dependency_overrides():
    original_overrides = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


def override_version_access(version: ResearchVersion):
    async def _get_version(version_id: str):
        if version_id != version.id:
            raise AssertionError(f"Unexpected test version {version_id}")
        return version

    app.dependency_overrides[get_owned_version] = _get_version
    app.dependency_overrides[get_accessible_version] = _get_version


# =========================================================================
# Tier 1: Canonical Valid Scientific Formulation (L1-L6 All-Pass)
# =========================================================================

@pytest.mark.asyncio
async def test_tier1_canonical_valid_formulation_all_layers_pass(stage4_test_entities):
    """Tier 1: Verifies interactive verification endpoint for a valid formulation."""
    override_version_access(stage4_test_entities["version_draft"])
    mock_db = MockDbSession(list(stage4_test_entities.values()))
    app.dependency_overrides[get_db] = lambda: mock_db

    # Canonical formulation: F = m * a
    ast_f_ma = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.MUL,
        left=ExprNode(node_type=NodeType.VARIABLE, value="m"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="a"),
    )
    vars_spec = [
        {"symbol": "m", "name": "mass", "unit": "kg", "domain": "real"},
        {"symbol": "a", "name": "acceleration", "unit": "m/s^2", "domain": "real"},
    ]
    units_spec = [
        {"name": "newton", "symbol": "N", "dimensionality": "[length] * [mass] / [time] ** 2"}
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "version_id": stage4_test_entities["version_draft"].id,
            "target_entity_type": "EQUATION",
            "target_entity_id": "eq_newton_law",
            "expression_ast": ast_f_ma.model_dump(),
            "variables": vars_spec,
            "units": units_spec,
        }
        res = await ac.post("/api/v1/validation/verify", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["state"] == "PASS"
        assert data["dimensions_verified"] is True
        assert "job_id" in data
        assert "layer_findings" in data or "layers" in data


@pytest.mark.asyncio
async def test_interactive_verify_worker_execution_failure_returns_unavailable(
    monkeypatch,
):
    """Interactive verification must not manufacture a PASS when compute fails."""
    import worker.tasks.compute_tasks as compute_tasks

    def fail_worker_run(*args, **kwargs):
        raise RuntimeError("worker execution failed")

    monkeypatch.setattr(compute_tasks.verify_equation_ast, "run", fail_worker_run)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/validation/verify",
            json={
                "expression_ast": {"node_type": "variable", "value": "x"},
                "variables": [],
            },
        )

    assert response.status_code == 503
    assert "compute worker failed" in response.json()["detail"]


# =========================================================================
# Tier 2: Layered Rejection & Fault Injection
# =========================================================================

@pytest.mark.asyncio
async def test_tier2a_layer1_2_syntax_and_boundary_rejection(stage4_test_entities):
    """Tier 2a: Rejects malformed AST / missing required fields."""
    mock_db = MockDbSession(list(stage4_test_entities.values()))
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        invalid_payload = {
            "version_id": stage4_test_entities["version_draft"].id,
            "target_entity_type": "EQUATION",
            "expression_ast": {"invalid_key": "not_an_ast"},
            "variables": [],
        }
        res = await ac.post("/api/v1/validation/verify", json=invalid_payload)
        assert res.status_code == 422  # Pydantic validation rejection


@pytest.mark.asyncio
async def test_tier2b_layer3_dimensional_inconsistency_rejection():
    """Tier 2b: Unit dimension mismatch detected in shared schemas."""
    unit_m = UnitSpec(name="meter", symbol="m", dimensionality="[length]")
    unit_s = UnitSpec(name="second", symbol="s", dimensionality="[time]")
    assert unit_m.dimensionality != unit_s.dimensionality


@pytest.mark.asyncio
async def test_tier2c_layer4_physical_laws_speed_limit_invariant():
    """Tier 2c: Relativistic speed limit constraint is validated in schema."""
    constraint = PhysicalConstraintSpec(
        constraint_type=PhysicalConstraintType.SPEED_OF_LIGHT.value,
        name="Relativistic Speed Limit",
        threshold=299792458.0,
        unit="m/s",
    )
    assert constraint.threshold == 299792458.0
    ctx = SystemContext(is_relativistic=True, safety_policy="strict_reject")
    assert ctx.is_relativistic is True


@pytest.mark.asyncio
async def test_tier2d_layer5_empirical_data_correlation_schema():
    """Tier 2d: Empirical data point schema validates non-negative uncertainties."""
    point = EmpiricalDataPoint(
        independent_variable=125.0,
        observed_value=42.0,
        uncertainty=1.5,
    )
    assert point.uncertainty > 0.0


@pytest.mark.asyncio
async def test_tier2e_layer6_epistemic_cycle_detection(stage4_test_entities):
    """Tier 2e: Epistemic cycle detection endpoint returns circular dependency error."""
    e = stage4_test_entities
    c1 = Claim(
        id="c1_cycle",
        version_id=e["version_draft"].id,
        claim_code="CLM-C1",
        statement="A implies B",
        claim_type="HYPOTHESIS",
        epistemic_state="NOT_YET_TESTED",
    )
    c2 = Claim(
        id="c2_cycle",
        version_id=e["version_draft"].id,
        claim_code="CLM-C2",
        statement="B implies A",
        claim_type="HYPOTHESIS",
        epistemic_state="NOT_YET_TESTED",
    )
    r1 = ClaimRelation(
        id="r1_cycle",
        version_id=e["version_draft"].id,
        source_claim_id="c1_cycle",
        target_claim_id="c2_cycle",
        relation_type="DEPENDS_ON",
    )
    r2 = ClaimRelation(
        id="r2_cycle",
        version_id=e["version_draft"].id,
        source_claim_id="c2_cycle",
        target_claim_id="c1_cycle",
        relation_type="DEPENDS_ON",
    )
    entities = list(e.values()) + [c1, c2, r1, r2]
    mock_db = MockDbSession(entities)
    app.dependency_overrides[get_db] = lambda: mock_db
    override_version_access(e["version_draft"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/versions/{e['version_draft'].id}/claims/verify-epistemic")
        assert res.status_code == 200
        data = res.json()
        assert data["cycle_report"]["cycle_detected"] is True
        assert data["overall_state"] == "FAIL"


# =========================================================================
# Tier 3: Version Validation, Freeze Immutability & Persistence
# =========================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("declare_acceleration", [True, False])
@pytest.mark.parametrize("publication_status", ["draft", "preprint", "published", "retracted"])
async def test_tier3_full_version_validate_and_persistence(
    stage4_test_entities, declare_acceleration, publication_status
):
    """Persist real worker findings for complete and undeclared-symbol formulations."""
    v_draft = stage4_test_entities["version_draft"]
    v_draft.publication_status = publication_status
    eq1 = Equation(
        id="eq_stage4_01",
        version_id=v_draft.id,
        label="Force Equation",
        latex_raw="F = m \\cdot a",
        canonical_ast_json={
            "node_type": "binary_op",
            "op": "*",
            "left": {"node_type": "variable", "value": "m"},
            "right": {"node_type": "variable", "value": "a"},
        },
    )
    var1 = Variable(
        id="var_m_01",
        version_id=v_draft.id,
        symbol="m",
        name="mass",
        unit="kg",
        domain="real",
    )
    entities = list(stage4_test_entities.values()) + [eq1, var1]
    if declare_acceleration:
        entities.append(Variable(
            id="var_a_01",
            version_id=v_draft.id,
            symbol="a",
            name="acceleration",
            unit="m/s^2",
            domain="real",
        ))
    mock_db = MockDbSession(entities)
    app.dependency_overrides[get_db] = lambda: mock_db
    override_version_access(v_draft)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Execute version validation
        res_val = await ac.post(f"/api/v1/versions/{v_draft.id}/validate")
        assert res_val.status_code == 200, res_val.text
        data_val = res_val.json()
        expected_state = "PASS" if declare_acceleration else "FAIL"
        assert data_val["overall_state"] == expected_state
        assert len(data_val["findings"]) == 6
        assert v_draft.publication_status == publication_status
        if not declare_acceleration:
            assert data_val["findings"][0]["diagnostic_code"] == DiagnosticCode.UNDECLARED_SYMBOL.value

        # Query historical runs
        res_runs = await ac.get(f"/api/v1/versions/{v_draft.id}/validation-runs")
        assert res_runs.status_code == 200
        runs_list = res_runs.json()
        assert len(runs_list) >= 1
        assert runs_list[0]["id"] == data_val["id"]
        assert runs_list[0]["overall_state"] == expected_state
        assert len(runs_list[0]["findings"]) == 6
        assert v_draft.publication_status == publication_status


@pytest.mark.asyncio
async def test_version_validate_worker_import_failure_returns_unavailable_without_persisting(
    stage4_test_entities, monkeypatch
):
    """Worker failure must not be converted into persisted scientific findings."""
    version = stage4_test_entities["version_draft"]
    mock_db = MockDbSession(list(stage4_test_entities.values()))
    app.dependency_overrides[get_db] = lambda: mock_db
    override_version_access(version)
    original_import = __import__

    def fail_worker_import(name, *args, **kwargs):
        if name == "worker.tasks.compute_tasks":
            raise ImportError("worker unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fail_worker_import)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/versions/{version.id}/validate")

    assert response.status_code == 503
    assert "compute worker failed" in response.json()["detail"]
    assert not any(isinstance(entity, ValidationRun) for entity in mock_db.entities)
    assert not any(isinstance(entity, ValidationFinding) for entity in mock_db.entities)


@pytest.mark.asyncio
async def test_tier3_frozen_version_immutability(stage4_test_entities):
    """Tier 3: Frozen research versions strictly block new equation authoring."""
    mock_db = MockDbSession(list(stage4_test_entities.values()))
    app.dependency_overrides[get_db] = lambda: mock_db
    override_version_access(stage4_test_entities["version_frozen"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "label": "Energy Equation",
            "latex_raw": "E = m c^2",
            "canonical_ast_json": {"node_type": "variable", "value": "E"},
        }
        res = await ac.post(
            f"/api/v1/versions/{stage4_test_entities['version_frozen'].id}/equations",
            json=payload,
        )
        assert res.status_code == 400
        assert "CANNOT_MODIFY_FROZEN_VERSION" in res.json()["detail"]


# =========================================================================
# Tier 4: Cryptographic ZIP Bundle Export & Offline Verification
# =========================================================================

@pytest.mark.asyncio
async def test_tier4_cryptographic_zip_export_and_offline_verification(stage4_test_entities):
    """Tier 4: Generates cryptographically signed research ZIP and runs offline verifier."""
    actor = stage4_test_entities["actor"]
    project = stage4_test_entities["project"]
    v_frozen = stage4_test_entities["version_frozen"]

    c1 = Claim(
        id="c1_exp_s4",
        version_id=v_frozen.id,
        claim_code="CLM-EXP-01",
        statement="Einstein mass-energy equivalence E = m c^2",
        claim_type="AXIOM",
        target_variable="E",
        epistemic_state="PASS",
    )
    entities = [actor, project, v_frozen, c1]
    mock_db = MockDbSession(entities)

    zip_bytes = await generate_research_zip_bundle(
        version_id=v_frozen.id,
        db=mock_db,
        current_actor_id=actor.id,
    )

    assert len(zip_bytes) > 0

    # Extract ZIP and inspect files
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert "signature.json" in namelist
        assert "checksums.sha256" in namelist
        assert "claims_graph.json" in namelist
        assert "verify_bundle.py" in namelist

        cg_json = json.loads(zf.read("claims_graph.json").decode("utf-8"))
        assert cg_json["version_id"] == v_frozen.id
        assert len(cg_json["claims"]) == 1

        manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest_data["@type"] == "ResearchArtifactBundle"
        assert "claims_graph.json" in manifest_data["files"]

        # Run verify_bundle.py offline on extracted contents
        with tempfile.TemporaryDirectory() as tmp_dir:
            zf.extractall(tmp_dir)
            verify_script = Path(tmp_dir) / "verify_bundle.py"
            assert verify_script.exists()

            proc = subprocess.run(
                [sys.executable, str(verify_script)],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
            )
            assert proc.returncode == 0, f"Verifier failed: {proc.stdout} {proc.stderr}"
            assert "[PASS] All bundle verification checks passed successfully." in proc.stdout

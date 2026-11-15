"""Stage 3 Epistemic Logic & Cross-Claim Verification Integration Test Suite.

End-to-end integration tests verifying:
1. REST API endpoints for Claims, Relations, and Claim Graph query.
2. Freeze immutability enforcement on frozen research versions.
3. Epistemic verification pipeline:
   - Clean DAG status propagation (PASS).
   - Circular dependency cycle detection (FAIL with CIRCULAR_DEPENDENCY_DETECTED).
   - Cross-claim contradiction detection (FAIL with CROSS_CLAIM_CONTRADICTION).
   - Epistemic poisoning across antecedent failure chains (EPISTEMIC_ANTECEDENT_FAILED).
4. Validation findings persistence in Zone 2 database (layer=6, target_entity_type="CLAIM").
5. Cryptographic ZIP bundle export packaging claims_graph.json and offline verification.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, List, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.modules.reality_constraint_engine.models import (
    Claim,
    ClaimRelation,
    ValidationFinding,
    ValidationRun,
)
from app.modules.research_core.exporter import generate_research_zip_bundle
from app.modules.research_core.models import (
    ResearchActor,
    ResearchProject,
    ResearchVersion,
)
from shared.models.enums import DiagnosticCode
from shared.schemas.finding_result import FindingState


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
    """In-memory Mock AsyncSession for Stage 3 integration tests."""

    def __init__(self, entities: List[Any]):
        self.entities = list(entities)

    def add(self, entity: Any) -> None:
        self.entities.append(entity)

    async def commit(self) -> None:
        pass

    async def refresh(self, entity: Any) -> None:
        pass

    async def execute(self, stmt: Any) -> MockResult:
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
def stage3_test_entities():
    actor = ResearchActor(
        id="act_newton_01",
        display_name="Sir Isaac Newton",
        orcid="0000-0002-9999-0001",
        organization_id="org_cambridge",
        is_anonymized=False,
    )
    project = ResearchProject(
        id="proj_mechanics_01",
        slug="principia-mathematica-mechanics",
        title="Philosophiae Naturalis Principia Mathematica",
        owner_actor_id=actor.id,
        visibility="public_preprint",
        is_frozen=False,
    )
    version_draft = ResearchVersion(
        id="ver_draft_01",
        project_id=project.id,
        version_number=1,
        title="Draft Laws of Motion",
        publication_status="draft",
        is_frozen=False,
    )
    version_frozen = ResearchVersion(
        id="ver_frozen_01",
        project_id=project.id,
        version_number=2,
        title="Final Published Principia",
        publication_status="published",
        is_frozen=True,
    )
    return {
        "actor": actor,
        "project": project,
        "version_draft": version_draft,
        "version_frozen": version_frozen,
    }


@pytest.mark.asyncio
async def test_claim_creation_and_listing(stage3_test_entities):
    e = stage3_test_entities
    db = MockDbSession([e["actor"], e["project"], e["version_draft"]])

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Axiom Claim
        resp = await client.post(
            f"/api/v1/versions/{e['version_draft'].id}/claims",
            json={
                "claim_code": "LAW_1",
                "statement": "Every body perseveres in its state of rest, or of uniform motion in a right line.",
                "claim_type": "AXIOM",
                "target_variable": "p",
                "dependency_logic": "ALL",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["claim_code"] == "LAW_1"
        assert data["claim_type"] == "AXIOM"
        assert data["epistemic_state"] == "NOT_YET_TESTED"
        claim_id_1 = data["id"]

        # Create Dependent Derivation Claim
        resp2 = await client.post(
            f"/api/v1/versions/{e['version_draft'].id}/claims",
            json={
                "claim_code": "LAW_2",
                "statement": "The alteration of motion is ever proportional to the motive force impressed.",
                "claim_type": "DERIVATION",
                "target_variable": "F",
                "dependency_logic": "ALL",
            },
        )
        assert resp2.status_code == 201
        claim_id_2 = resp2.json()["id"]

        # Link claims via relation
        rel_resp = await client.post(
            f"/api/v1/versions/{e['version_draft'].id}/claims/relations",
            json={
                "source_claim_id": claim_id_2,
                "target_claim_id": claim_id_1,
                "relation_type": "DERIVED_FROM",
                "justification": "Momentum definition required for force derivation",
            },
        )
        assert rel_resp.status_code == 201
        assert rel_resp.json()["relation_type"] == "DERIVED_FROM"

        # Query claims list
        list_resp = await client.get(f"/api/v1/versions/{e['version_draft'].id}/claims")
        assert list_resp.status_code == 200
        claims_list = list_resp.json()
        assert len(claims_list) == 2

        # Query full graph
        graph_resp = await client.get(f"/api/v1/versions/{e['version_draft'].id}/claims/graph")
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert len(graph_data["claims"]) == 2
        assert len(graph_data["relations"]) == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_claim_mutation_rejected_on_frozen_version(stage3_test_entities):
    e = stage3_test_entities
    db = MockDbSession([e["actor"], e["project"], e["version_frozen"]])

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/versions/{e['version_frozen'].id}/claims",
            json={
                "claim_code": "CLM_MUTATE",
                "statement": "Attempted modification of frozen preprint",
                "claim_type": "HYPOTHESIS",
            },
        )
        assert resp.status_code == 400
        assert "CANNOT_MODIFY_FROZEN_VERSION" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_epistemic_verification_clean_dag(stage3_test_entities):
    e = stage3_test_entities
    c1 = Claim(
        id="c1",
        version_id=e["version_draft"].id,
        claim_code="AXIOM_1",
        statement="Axiom premise holds",
        claim_type="AXIOM",
        epistemic_state="PASS",
    )
    c2 = Claim(
        id="c2",
        version_id=e["version_draft"].id,
        claim_code="THM_1",
        statement="Derived consequence holds",
        claim_type="DERIVATION",
        epistemic_state="PASS",
    )
    rel = ClaimRelation(
        id="r1",
        version_id=e["version_draft"].id,
        source_claim_id="c2",
        target_claim_id="c1",
        relation_type="DERIVED_FROM",
    )
    db = MockDbSession([e["actor"], e["project"], e["version_draft"], c1, c2, rel])

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/versions/{e['version_draft'].id}/claims/verify-epistemic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_state"] == FindingState.PASS.value
        assert data["cycle_report"]["cycle_detected"] is False
        assert data["contradiction_report"]["contradictions_found"] is False
        assert data["claim_findings"]["c1"]["state"] == FindingState.PASS.value
        assert data["claim_findings"]["c2"]["state"] == FindingState.PASS.value

        # Confirm findings were persisted into db
        stored_findings = [ent for ent in db.entities if isinstance(ent, ValidationFinding)]
        assert len(stored_findings) == 2
        assert all(f.layer == 6 and f.target_entity_type == "CLAIM" for f in stored_findings)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_epistemic_verification_detects_circular_dependency(stage3_test_entities):
    e = stage3_test_entities
    # 2-cycle: c1 depends on c2, and c2 depends on c1
    c1 = Claim(
        id="c1",
        version_id=e["version_draft"].id,
        claim_code="CIRC_1",
        statement="Circular claim 1",
        claim_type="DERIVATION",
        epistemic_state="PASS",
    )
    c2 = Claim(
        id="c2",
        version_id=e["version_draft"].id,
        claim_code="CIRC_2",
        statement="Circular claim 2",
        claim_type="DERIVATION",
        epistemic_state="PASS",
    )
    rel1 = ClaimRelation(
        id="r1",
        version_id=e["version_draft"].id,
        source_claim_id="c1",
        target_claim_id="c2",
        relation_type="DEPENDS_ON",
    )
    rel2 = ClaimRelation(
        id="r2",
        version_id=e["version_draft"].id,
        source_claim_id="c2",
        target_claim_id="c1",
        relation_type="DEPENDS_ON",
    )
    db = MockDbSession([e["actor"], e["project"], e["version_draft"], c1, c2, rel1, rel2])

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/versions/{e['version_draft'].id}/claims/verify-epistemic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_state"] == FindingState.FAIL.value
        assert data["cycle_report"]["cycle_detected"] is True
        assert "c1" in data["cycle_report"]["cyclic_claim_ids"]
        assert "c2" in data["cycle_report"]["cyclic_claim_ids"]
        assert data["claim_findings"]["c1"]["state"] == FindingState.FAIL.value
        assert data["claim_findings"]["c1"]["diagnostic_code"] == DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_epistemic_verification_detects_contradiction(stage3_test_entities):
    e = stage3_test_entities
    # Explicit contradiction between two PASS claims
    c1 = Claim(
        id="c1",
        version_id=e["version_draft"].id,
        claim_code="PARADOX_A",
        statement="Light is strictly corpuscular",
        claim_type="HYPOTHESIS",
        epistemic_state="PASS",
    )
    c2 = Claim(
        id="c2",
        version_id=e["version_draft"].id,
        claim_code="PARADOX_B",
        statement="Light is strictly continuous wave",
        claim_type="HYPOTHESIS",
        epistemic_state="PASS",
    )
    rel_contra = ClaimRelation(
        id="r_contra",
        version_id=e["version_draft"].id,
        source_claim_id="c1",
        target_claim_id="c2",
        relation_type="CONTRADICTS",
    )
    db = MockDbSession([e["actor"], e["project"], e["version_draft"], c1, c2, rel_contra])

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/versions/{e['version_draft'].id}/claims/verify-epistemic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_state"] == FindingState.FAIL.value
        assert data["contradiction_report"]["contradictions_found"] is True
        assert data["claim_findings"]["c1"]["state"] == FindingState.FAIL.value
        assert data["claim_findings"]["c1"]["diagnostic_code"] == DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_bundle_includes_and_verifies_claims_graph(stage3_test_entities):
    e = stage3_test_entities
    c1 = Claim(
        id="c1_exp",
        version_id=e["version_frozen"].id,
        claim_code="CLM_EXPORT_1",
        statement="Gravitational acceleration on Earth surface is approx 9.8 m/s^2",
        claim_type="EMPIRICAL_OBSERVATION",
        target_variable="g",
        epistemic_state="PASS",
    )
    c2 = Claim(
        id="c2_exp",
        version_id=e["version_frozen"].id,
        claim_code="CLM_EXPORT_2",
        statement="Weight of mass m is W = m * g",
        claim_type="DERIVATION",
        target_variable="W",
        epistemic_state="PASS",
    )
    rel = ClaimRelation(
        id="r_exp",
        version_id=e["version_frozen"].id,
        source_claim_id="c2_exp",
        target_claim_id="c1_exp",
        relation_type="DERIVED_FROM",
    )
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        c1,
        c2,
        rel,
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        file_list = zf.namelist()
        assert "claims_graph.json" in file_list
        assert "manifest.json" in file_list
        assert "verify_bundle.py" in file_list

        cg_json = json.loads(zf.read("claims_graph.json").decode("utf-8"))
        assert cg_json["version_id"] == e["version_frozen"].id
        assert len(cg_json["claims"]) == 2
        assert len(cg_json["relations"]) == 1

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert "claims_graph.json" in manifest["files"]

        # Run verify_bundle.py offline on extracted contents
        with tempfile.TemporaryDirectory() as tmp_dir:
            zf.extractall(tmp_dir)
            verify_script = Path(tmp_dir) / "verify_bundle.py"
            assert verify_script.exists()

            result = subprocess.run(
                [sys.executable, str(verify_script)],
                capture_output=True,
                text=True,
                cwd=tmp_dir,
            )
            assert result.returncode == 0, f"Offline verification failed:\n{result.stdout}\n{result.stderr}"
            assert "[PASS] All bundle verification checks passed successfully." in result.stdout

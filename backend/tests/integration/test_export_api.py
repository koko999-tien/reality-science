import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.modules.research_core.models import (
    Equation,
    ResearchActor,
    ResearchProject,
    ResearchVersion,
    ValidationFinding,
    ValidationRun,
    Variable,
)
from app.modules.iam_governance.models import UserAccount
from httpx import ASGITransport, AsyncClient


class MockResult:
    def __init__(self, items):
        self._items = items

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class MockDbSession:
    """Mock AsyncSession providing in-memory entity querying for API integration tests."""

    def __init__(self, entities):
        self.entities = list(entities)
        self.info = {}

    async def execute(self, stmt, _params=None):
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
                    attr_name = re.sub(r"_\d+$", "", param_name)
                    if hasattr(item, attr_name) and getattr(item, attr_name) != param_val:
                        match = False
                        break
                if match:
                    filtered.append(item)
            return MockResult(filtered)
        return MockResult(candidates)


@pytest.fixture
def seeded_db():
    actor = ResearchActor(
        id="actor_planck_001",
        display_name="Dr. Max Planck",
        orcid="0000-0002-1825-0097",
        organization_id="org_mpg_01",
        is_anonymized=False,
    )
    actor.email = "max.planck@quantum-institute.de"
    actor.user_account_id = "user_acc_planck_sec_999"
    user = UserAccount(
        id=actor.user_account_id,
        email="max.planck@example.test",
        hashed_password="unused-test-hash",
        is_active=True,
    )
    user.actor = actor

    # Public project
    public_project = ResearchProject(
        id="proj_planck_law",
        slug="blackbody-radiation-bounds",
        title="Blackbody Radiation Quantum Bounds",
        description="Derivation of spectral radiance and ultraviolet catastrophe resolution.",
        owner_actor_id=actor.id,
        organization_id=actor.organization_id,
        visibility="public_preprint",
        is_frozen=True,
    )

    # Frozen version
    ver_frozen = ResearchVersion(
        id="ver_planck_frozen_100",
        project_id=public_project.id,
        version_number=1,
        title="Planck Law Formulation v1",
        content_hash="c0ffee1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        publication_status="published",
        is_frozen=True,
    )

    # Unfrozen version (draft)
    ver_draft = ResearchVersion(
        id="ver_planck_draft_200",
        project_id=public_project.id,
        version_number=2,
        title="Draft Under Computation v2",
        publication_status="draft",
        is_frozen=False,
    )

    # Private project & frozen version
    private_project = ResearchProject(
        id="proj_private_stealth",
        slug="classified-quantum-teleportation",
        title="Classified Quantum Teleportation",
        description="Private institutional draft.",
        owner_actor_id=actor.id,
        organization_id=actor.organization_id,
        visibility="private_draft",
        is_frozen=True,
    )

    ver_private_frozen = ResearchVersion(
        id="ver_private_frozen_300",
        project_id=private_project.id,
        version_number=1,
        title="Private Snapshot v1",
        publication_status="published",
        is_frozen=True,
    )

    # Variables
    var_nu = Variable(
        id="var_nu_01",
        version_id=ver_frozen.id,
        symbol="nu",
        name="Frequency",
        unit="1 / second",
        domain="positive_real",
        latex_presentation=r"\nu",
    )

    var_t = Variable(
        id="var_t_02",
        version_id=ver_frozen.id,
        symbol="T",
        name="Thermodynamic Temperature",
        unit="kelvin",
        domain="positive_real",
        latex_presentation="T",
    )

    # Equation
    eq_planck = Equation(
        id="eq_planck_01",
        version_id=ver_frozen.id,
        label="SpectralRadiance",
        latex_raw=r"B(\nu, T) = \frac{2 h \nu^3}{c^2} \frac{1}{e^{\frac{h \nu}{k_B T}} - 1}",
        canonical_ast_json={
            "node_type": "binary_op",
            "op": "*",
            "left": {
                "node_type": "constant",
                "value": 2.0,
            },
            "right": {
                "node_type": "variable",
                "value": "nu",
            },
        },
        sympy_expr="2.0 * nu",
    )

    # Validation Run & Findings
    val_run = ValidationRun(
        id="run_planck_001",
        version_id=ver_frozen.id,
        status="completed",
        overall_state="PASS",
    )

    finding_1 = ValidationFinding(
        id="find_p1",
        run_id=val_run.id,
        layer=1,
        target_entity_type="EQUATION",
        target_entity_id=eq_planck.id,
        job_id="job_planck_syntax_01",
        state="PASS",
        diagnostic_code="VALIDATION_PASSED",
        message="Valid Layer 1 mathematical AST.",
        dimensions_verified=True,
        diagnostics={"details": ["Complexity depth <= 15"]},
    )

    finding_2 = ValidationFinding(
        id="find_p2",
        run_id=val_run.id,
        layer=2,
        target_entity_type="EQUATION",
        target_entity_id=eq_planck.id,
        job_id="job_planck_dim_02",
        state="PASS",
        diagnostic_code="DIMENSIONAL_HOMOGENEITY_VERIFIED",
        message="Layer 2 dimensional consistency confirmed via Pint physical unit ontology.",
        dimensions_verified=True,
        diagnostics={"details": ["Pint verified [length] ** 2 / [time] ** 3"]},
    )

    finding_3 = ValidationFinding(
        id="find_p3",
        run_id=val_run.id,
        layer=3,
        target_entity_type="EQUATION",
        target_entity_id=eq_planck.id,
        job_id="job_planck_bound_03",
        state="PASS",
        diagnostic_code="BOUNDARY_LIMIT_CONVERGED",
        message="Layer 3 Rayleigh-Jeans low-frequency limit converged without singularity.",
        dimensions_verified=True,
        diagnostics={"details": ["Limit nu -> 0+ verified"]},
    )

    entities = [
        user,
        actor,
        public_project,
        private_project,
        ver_frozen,
        ver_draft,
        ver_private_frozen,
        var_nu,
        var_t,
        eq_planck,
        val_run,
        finding_1,
        finding_2,
        finding_3,
    ]
    return MockDbSession(entities)


@pytest.fixture
def override_db(seeded_db):
    original_overrides = dict(app.dependency_overrides)
    original_jwt_secret = settings.jwt_secret_key
    settings.jwt_secret_key = "test-only-jwt-signing-key-at-least-32-bytes"

    async def _get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    settings.jwt_secret_key = original_jwt_secret


@pytest.mark.asyncio
async def test_export_unfrozen_draft_rejected_with_400(override_db):
    """POST /api/v1/versions/{version_id}/export-zip must reject unfrozen drafts with HTTP 400 CANNOT_EXPORT_UNFROZEN_DRAFT."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/versions/ver_planck_draft_200/export-zip")

    assert response.status_code == 400
    assert response.json()["detail"] == "CANNOT_EXPORT_UNFROZEN_DRAFT"


@pytest.mark.asyncio
async def test_export_nonexistent_version_rejected_with_404(override_db):
    """POST /api/v1/versions/{version_id}/export-zip must return HTTP 404 for unknown version IDs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/versions/ver_non_existent_9999/export-zip")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_export_private_draft_unauthorized_rejected_with_404(override_db):
    """Caller-supplied actor identity must not authorize private-draft export."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Without owner credentials
        response = await ac.post(
            "/api/v1/versions/ver_private_frozen_300/export-zip",
            headers={"X-Actor-Id": "actor_planck_001"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_private_draft_anonymous_is_hidden(override_db):
    """Private export requires a principal, not a caller-supplied identity header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/versions/ver_private_frozen_300/export-zip",
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_private_draft_remains_hidden_when_signing_key_is_invalid(override_db):
    original_secret = settings.jwt_secret_key
    settings.jwt_secret_key = ""
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/versions/ver_private_frozen_300/export-zip")
    finally:
        settings.jwt_secret_key = original_secret

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_private_draft_allows_authenticated_owner(override_db):
    token = create_access_token("user_acc_planck_sec_999")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/versions/ver_private_frozen_300/export-zip",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


@pytest.mark.asyncio
async def test_export_frozen_version_returns_valid_zip_stream(override_db):
    """POST /api/v1/versions/{version_id}/export-zip exports public frozen preprint with HTTP 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/versions/ver_planck_frozen_100/export-zip")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert 'attachment; filename="research_bundle_ver_planck_frozen_100.zip"' in response.headers["content-disposition"]

    zip_bytes = response.content
    assert len(zip_bytes) > 0

    # Test in-memory archive reading
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert "checksums.sha256" in namelist
        assert "signature.json" in namelist
        assert "paper.md" in namelist
        assert "verify_bundle.py" in namelist
        assert "metadata/actor.json" in namelist
        assert "math/variables.json" in namelist
        assert "validation/validation_report.json" in namelist

        # Assert Zero PII in extracted actor metadata
        actor_data = json.loads(zf.read("metadata/actor.json").decode("utf-8"))
        assert actor_data["id"] == "actor_planck_001"
        assert actor_data["display_name"] == "Dr. Max Planck"
        assert "email" not in actor_data
        assert "password" not in actor_data
        assert "hashed_password" not in actor_data
        assert "user_account_id" not in actor_data


@pytest.mark.asyncio
async def test_export_zip_archive_runs_verify_bundle_successfully(override_db):
    """Unzips exported ZIP archive to disk and executes standalone verify_bundle.py successfully."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/versions/ver_planck_frozen_100/export-zip")

    assert response.status_code == 200
    zip_bytes = response.content

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_file_path = tmp_path / "downloaded_bundle.zip"
        zip_file_path.write_bytes(zip_bytes)

        # 1. Test running verify_bundle.py directly via --zip
        extracted_dir = tmp_path / "unzipped"
        extracted_dir.mkdir()
        with zipfile.ZipFile(zip_file_path, "r") as zf:
            zf.extractall(extracted_dir)

        verifier_path = extracted_dir / "verify_bundle.py"
        assert verifier_path.exists()

        # Run offline verifier inside extracted directory with platform secret
        proc = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py", "--secret", settings.jwt_secret_key],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode == 0, f"Verifier failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        assert "[PASS] All bundle verification checks passed successfully." in proc.stdout
        assert "JSON-LD manifest and file catalog verified." in proc.stdout
        assert "Platform HMAC-SHA256 signature verified with secret key." in proc.stdout
        assert "Zero PII verified: no email, password, or user account ID present." in proc.stdout
        assert "Verified 1 equation AST(s)." in proc.stdout

        # 2. Test running verify_bundle.py with --zip flag
        proc_zip = subprocess.run(  # noqa: ASYNC221
            [sys.executable, str(verifier_path), "--zip", str(zip_file_path), "--secret", settings.jwt_secret_key],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc_zip.returncode == 0, f"Zip verifier failed:\nSTDOUT:\n{proc_zip.stdout}\nSTDERR:\n{proc_zip.stderr}"
        assert "[PASS] All bundle verification checks passed successfully." in proc_zip.stdout

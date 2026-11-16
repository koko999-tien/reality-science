import hashlib
import hmac
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
from app.modules.research_core.exporter import generate_research_zip_bundle
from app.modules.research_core.models import (
    Equation,
    ResearchActor,
    ResearchProject,
    ResearchVersion,
    ValidationFinding,
    ValidationRun,
    Variable,
)


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
    """Mock AsyncSession for unit tests executing SQLAlchemy statements against in-memory objects."""

    def __init__(self, entities):
        self.entities = list(entities)
        self.info = {}

    async def execute(self, stmt):
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
def mock_research_entities():
    actor = ResearchActor(
        id="act_curie_001",
        display_name="Dr. Marie Curie",
        orcid="0000-0001-2345-6789",
        organization_id="org_sorbonne_01",
        is_anonymized=False,
    )
    # Add accidental attributes to test strict PII stripping
    actor.email = "marie.curie@radium-lab.edu"
    actor.user_account_id = "user_acc_sensitive_999"

    project = ResearchProject(
        id="proj_rad_001",
        slug="radium-decay-kinetics",
        title="Radium Alpha Decay Kinetics",
        description="Comprehensive study of radioactive decay rates and boundary stability.",
        owner_actor_id=actor.id,
        organization_id=actor.organization_id,
        visibility="public_preprint",
        is_frozen=True,
    )

    version_frozen = ResearchVersion(
        id="ver_frozen_001",
        project_id=project.id,
        version_number=1,
        title="Initial Verified Preprint v1",
        content_hash="a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
        publication_status="published",
        is_frozen=True,
    )

    version_draft = ResearchVersion(
        id="ver_draft_002",
        project_id=project.id,
        version_number=2,
        title="Unpublished Draft v2",
        publication_status="draft",
        is_frozen=False,
    )

    var_n = Variable(
        id="var_01",
        version_id=version_frozen.id,
        symbol="N",
        name="Nuclei Count",
        unit="dimensionless",
        domain="positive_real",
        latex_presentation="N(t)",
    )

    var_lambda = Variable(
        id="var_02",
        version_id=version_frozen.id,
        symbol="decay_const",
        name="Decay Constant",
        unit="1 / second",
        domain="positive_real",
        latex_presentation="\\lambda",
    )

    eq_decay = Equation(
        id="eq_01",
        version_id=version_frozen.id,
        label="RadioactiveDecay",
        latex_raw=r"\frac{dN}{dt} = -\lambda N",
        canonical_ast_json={
            "node_type": "binary_op",
            "op": "*",
            "left": {
                "node_type": "unary_op",
                "op": "neg",
                "left": {"node_type": "variable", "value": "decay_const"},
            },
            "right": {"node_type": "variable", "value": "N"},
        },
        sympy_expr="-decay_const * N",
    )

    run = ValidationRun(
        id="run_01",
        version_id=version_frozen.id,
        status="completed",
        overall_state="PASS",
    )

    finding = ValidationFinding(
        id="finding_01",
        run_id=run.id,
        layer=1,
        target_entity_type="EQUATION",
        target_entity_id=eq_decay.id,
        job_id="job_val_12345678",
        state="PASS",
        diagnostic_code="VALIDATION_PASSED",
        message="AST syntax and complexity guards passed successfully.",
        dimensions_verified=True,
        diagnostics={"details": ["Node count: 4", "Depth: 3"]},
    )

    return {
        "actor": actor,
        "project": project,
        "version_frozen": version_frozen,
        "version_draft": version_draft,
        "variables": [var_n, var_lambda],
        "equations": [eq_decay],
        "runs": [run],
        "findings": [finding],
    }


@pytest.mark.asyncio
async def test_generate_research_zip_bundle_structure_and_files(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        e["variables"][0],
        e["variables"][1],
        e["equations"][0],
        e["runs"][0],
        e["findings"][0],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    # Read zip entries
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        file_list = zf.namelist()

        # Check all required top-level and directory entries
        assert "manifest.json" in file_list
        assert "checksums.sha256" in file_list
        assert "signature.json" in file_list
        assert "paper.md" in file_list
        assert "verify_bundle.py" in file_list
        assert "metadata/project.json" in file_list
        assert "metadata/version.json" in file_list
        assert "metadata/actor.json" in file_list
        assert "math/variables.json" in file_list
        assert "math/units.json" in file_list
        assert "validation/validation_report.json" in file_list
        assert any(f.startswith("math/equations/eq_") and f.endswith(".json") for f in file_list)

        # 1. Inspect manifest.json
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["@context"] == "https://w3id.org/ro/crate/1.1/context"
        assert manifest["@type"] == "ResearchArtifactBundle"
        assert manifest["version_id"] == e["version_frozen"].id
        assert manifest["version_number"] == 1
        assert manifest["project_slug"] == e["project"].slug
        assert manifest["project_title"] == e["project"].title
        assert manifest["license"] == "CC-BY-4.0"
        assert manifest["author"]["name"] == "Dr. Marie Curie"
        assert manifest["author"]["orcid"] == "0000-0001-2345-6789"
        assert "paper.md" in manifest["files"]
        assert "metadata/actor.json" in manifest["files"]

        # 2. Inspect ZERO PII in metadata/actor.json
        actor_data = json.loads(zf.read("metadata/actor.json").decode("utf-8"))
        assert actor_data["id"] == e["actor"].id
        assert actor_data["display_name"] == "Dr. Marie Curie"
        assert actor_data["orcid"] == "0000-0001-2345-6789"
        assert "email" not in actor_data
        assert "password" not in actor_data
        assert "hashed_password" not in actor_data
        assert "user_account_id" not in actor_data

        # 3. Inspect checksums.sha256 format
        checksums_text = zf.read("checksums.sha256").decode("utf-8")
        for line in checksums_text.strip().split("\n"):
            assert re.match(r"^[a-f0-9]{64}  \S+", line), f"Invalid checksum line: {line}"
            sha, path = line.split("  ", 1)
            file_bytes = zf.read(path)
            assert hashlib.sha256(file_bytes).hexdigest() == sha

        # 4. Inspect signature.json
        sig = json.loads(zf.read("signature.json").decode("utf-8"))
        assert sig["algorithm"] == "HMAC-SHA256"
        manifest_raw = zf.read("manifest.json")
        assert sig["manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest()
        expected_hmac = hmac.new(settings.jwt_secret_key.encode("utf-8"), manifest_raw, hashlib.sha256).hexdigest()
        assert sig["signature"] == expected_hmac

        # 5. Inspect paper.md
        paper = zf.read("paper.md").decode("utf-8")
        assert f"# {e['project'].title}" in paper
        assert "Dr. Marie Curie" in paper
        assert "## Mathematical Formulations" in paper
        assert r"\frac{dN}{dt} = -\lambda N" in paper
        assert "## Variables & Dimensional Units" in paper
        assert "## Validation Findings Summary" in paper
        assert "## Integrity Checksums" in paper


@pytest.mark.asyncio
async def test_unfrozen_draft_rejected_raises_value_error(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_draft"],
    ])

    with pytest.raises(ValueError, match="CANNOT_EXPORT_UNFROZEN_DRAFT"):
        await generate_research_zip_bundle(
            version_id=e["version_draft"].id,
            db=db,
            current_actor_id=e["actor"].id,
        )


@pytest.mark.asyncio
async def test_version_not_found_raises_value_error(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([])

    with pytest.raises(ValueError, match="Version not found"):
        await generate_research_zip_bundle(
            version_id="non-existent-version-uuid",
            db=db,
            current_actor_id=e["actor"].id,
        )


@pytest.mark.asyncio
async def test_private_draft_unauthorized_actor_rejected(mock_research_entities):
    e = mock_research_entities
    private_project = ResearchProject(
        id="proj_private_001",
        slug="classified-fusion-experiment",
        title="Classified Fusion Experiment",
        owner_actor_id=e["actor"].id,
        visibility="private_draft",
        is_frozen=True,
    )
    frozen_version = ResearchVersion(
        id="ver_private_frozen",
        project_id=private_project.id,
        version_number=1,
        title="Internal Snapshot",
        is_frozen=True,
    )
    db = MockDbSession([
        e["actor"],
        private_project,
        frozen_version,
    ])

    with pytest.raises(PermissionError, match="ACCESS_DENIED"):
        await generate_research_zip_bundle(
            version_id=frozen_version.id,
            db=db,
            current_actor_id="different_unauthorized_actor",
        )


@pytest.mark.asyncio
async def test_private_draft_authorized_owner_allowed(mock_research_entities):
    e = mock_research_entities
    private_project = ResearchProject(
        id="proj_private_001",
        slug="classified-fusion-experiment",
        title="Classified Fusion Experiment",
        owner_actor_id=e["actor"].id,
        visibility="private_draft",
        is_frozen=True,
    )
    frozen_version = ResearchVersion(
        id="ver_private_frozen",
        project_id=private_project.id,
        version_number=1,
        title="Internal Snapshot",
        is_frozen=True,
    )
    db = MockDbSession([
        e["actor"],
        private_project,
        frozen_version,
    ])

    bundle = await generate_research_zip_bundle(
        version_id=frozen_version.id,
        db=db,
        current_actor_id=e["actor"].id,
    )
    assert len(bundle) > 0


@pytest.mark.asyncio
async def test_verify_bundle_script_passes_on_valid_bundle(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        e["variables"][0],
        e["variables"][1],
        e["equations"][0],
        e["runs"][0],
        e["findings"][0],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_file = tmp_path / "bundle.zip"
        zip_file.write_bytes(zip_bytes)

        # First extract to test standalone script directly in directory
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(extracted_dir)

        proc = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py", "--secret", settings.jwt_secret_key],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode == 0, f"Verifier failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        assert "[PASS] All bundle verification checks passed successfully." in proc.stdout

        # Test with --zip flag
        proc_zip = subprocess.run(  # noqa: ASYNC221
            [sys.executable, str(extracted_dir / "verify_bundle.py"), "--zip", str(zip_file), "--secret", settings.jwt_secret_key],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_zip.returncode == 0
        assert "[PASS] All bundle verification checks passed successfully." in proc_zip.stdout


@pytest.mark.asyncio
async def test_verify_bundle_detects_tampering(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        e["variables"][0],
        e["variables"][1],
        e["equations"][0],
        e["runs"][0],
        e["findings"][0],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_file = tmp_path / "bundle.zip"
        zip_file.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(tmp_path)

        # Tamper with paper.md
        paper_file = tmp_path / "paper.md"
        paper_file.write_text(paper_file.read_text(encoding="utf-8") + "\n# MALICIOUS TAMPERING", encoding="utf-8")

        proc = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode != 0
        assert "[FAIL]" in proc.stdout
        assert "SHA-256 mismatch for paper.md" in proc.stdout


@pytest.mark.asyncio
async def test_verify_bundle_detects_pii_leak(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        e["variables"][0],
        e["variables"][1],
        e["equations"][0],
        e["runs"][0],
        e["findings"][0],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            zf.extractall(tmp_path)

        # Inject PII into metadata/actor.json
        actor_file = tmp_path / "metadata" / "actor.json"
        actor_json = json.loads(actor_file.read_text(encoding="utf-8"))
        actor_json["email"] = "leaked_researcher@mit.edu"
        actor_file.write_text(json.dumps(actor_json, indent=2), encoding="utf-8")

        # Update checksums.sha256 so checksum step passes and PII step catches it
        new_actor_sha = hashlib.sha256(actor_file.read_bytes()).hexdigest()
        chk_file = tmp_path / "checksums.sha256"
        lines = []
        for line in chk_file.read_text(encoding="utf-8").splitlines():
            if "metadata/actor.json" in line:
                lines.append(f"{new_actor_sha}  metadata/actor.json")
            else:
                lines.append(line)
        chk_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        proc = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode != 0
        assert "PII LEAK DETECTED" in proc.stdout


@pytest.mark.asyncio
async def test_verify_bundle_detects_untracked_files(mock_research_entities):
    e = mock_research_entities
    db = MockDbSession([
        e["actor"],
        e["project"],
        e["version_frozen"],
        e["variables"][0],
        e["variables"][1],
        e["equations"][0],
        e["runs"][0],
        e["findings"][0],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=e["version_frozen"].id,
        db=db,
        current_actor_id=e["actor"].id,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_file = tmp_path / "bundle.zip"
        zip_file.write_bytes(zip_bytes)

        # 1. Test untracked file in extracted directory
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(extracted_dir)

        # Inject untracked malicious.sh into extracted directory
        injected_file = extracted_dir / "malicious.sh"
        injected_file.write_text("#!/bin/bash\necho 'malicious payload'\n", encoding="utf-8")

        proc_dir = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py", "--secret", settings.jwt_secret_key],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc_dir.returncode != 0
        assert "[FAIL]" in proc_dir.stdout
        assert "Untracked / undeclared file(s) detected in bundle" in proc_dir.stdout
        assert "malicious.sh" in proc_dir.stdout

        # 2. Test untracked file injected into ZIP archive directly
        tampered_zip = tmp_path / "tampered_bundle.zip"
        with (
            zipfile.ZipFile(zip_file, "r") as src_zip,
            zipfile.ZipFile(tampered_zip, "w") as dst_zip,
        ):
            for item in src_zip.infolist():
                dst_zip.writestr(item, src_zip.read(item.filename))
            dst_zip.writestr("malicious_in_zip.sh", "#!/bin/sh\nexit 1\n")

        proc_zip = subprocess.run(  # noqa: ASYNC221
            [sys.executable, str(extracted_dir / "verify_bundle.py"), "--zip", str(tampered_zip), "--secret", settings.jwt_secret_key],
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc_zip.returncode != 0
        assert "[FAIL]" in proc_zip.stdout
        assert "Untracked / undeclared file(s) detected in bundle" in proc_zip.stdout
        assert "malicious_in_zip.sh" in proc_zip.stdout

        # 3. Test adversarial bypass: injected file added to checksums.sha256 (FINDING-M8-02)
        # An adversary attempts to bypass detection by declaring the malicious file in checksums.sha256
        poisoned_file = extracted_dir / "malicious_poison.sh"
        poisoned_content = b"#!/bin/bash\necho 'rootkit payload'\n"
        poisoned_file.write_bytes(poisoned_content)
        poisoned_sha = hashlib.sha256(poisoned_content).hexdigest()

        # Append poisoned entry to checksums.sha256
        chk_file = extracted_dir / "checksums.sha256"
        chk_file.write_text(
            chk_file.read_text(encoding="utf-8") + f"{poisoned_sha}  malicious_poison.sh\n",
            encoding="utf-8",
        )

        # Remove the previously injected un-checksummed malicious.sh so only the poisoned attack vector is active
        injected_file.unlink()

        proc_poison = subprocess.run(  # noqa: ASYNC221
            [sys.executable, "verify_bundle.py", "--secret", settings.jwt_secret_key],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc_poison.returncode != 0
        assert "[FAIL]" in proc_poison.stdout
        assert "Untracked / undeclared file(s) listed in checksums.sha256" in proc_poison.stdout
        assert "malicious_poison.sh" in proc_poison.stdout
        assert "Untracked / undeclared file(s) detected in bundle" in proc_poison.stdout

        # 4. Test poisoned ZIP archive with injected file in checksums.sha256 via --zip
        poisoned_zip = tmp_path / "poisoned_bundle.zip"
        with (
            zipfile.ZipFile(zip_file, "r") as src_zip,
            zipfile.ZipFile(poisoned_zip, "w") as dst_zip,
        ):
            existing_chk = src_zip.read("checksums.sha256").decode("utf-8")
            poison_zip_content = b"#!/bin/sh\nexit 1337\n"
            poison_zip_sha = hashlib.sha256(poison_zip_content).hexdigest()
            updated_chk = existing_chk + f"{poison_zip_sha}  malicious_in_zip_poison.sh\n"

            for item in src_zip.infolist():
                if item.filename == "checksums.sha256":
                    dst_zip.writestr(item, updated_chk.encode("utf-8"))
                else:
                    dst_zip.writestr(item, src_zip.read(item.filename))
            dst_zip.writestr("malicious_in_zip_poison.sh", poison_zip_content)

        proc_zip_poison = subprocess.run(  # noqa: ASYNC221
            [sys.executable, str(extracted_dir / "verify_bundle.py"), "--zip", str(poisoned_zip), "--secret", settings.jwt_secret_key],
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc_zip_poison.returncode != 0
        assert "[FAIL]" in proc_zip_poison.stdout
        assert "Untracked / undeclared file(s) listed in checksums.sha256" in proc_zip_poison.stdout
        assert "malicious_in_zip_poison.sh" in proc_zip_poison.stdout
        assert "Untracked / undeclared file(s) detected in bundle" in proc_zip_poison.stdout

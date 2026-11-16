import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, patch

from app.modules.compute_orchestrator.dispatcher import dispatch_compute_job
from app.modules.compute_orchestrator.ingestion import fetch_finding_result
from app.modules.reality_constraint_engine.models import (
    Equation,
    Variable,
)
from app.modules.research_core.exporter import (
    generate_research_zip_bundle,
)
from app.modules.research_core.models import (
    ResearchActor,
    ResearchProject,
    ResearchVersion,
    ValidationFinding,
    ValidationRun,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
    try_eval_constant_ast,
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
    """In-memory Mock AsyncSession for stage 1 integration tests."""

    def __init__(self, entities):
        self.entities = list(entities)

    async def execute(self, stmt):
        model_cls = stmt.column_descriptions[0]["type"]
        params = stmt.compile().params
        candidates = [e for e in self.entities if isinstance(e, model_cls)]

        if params:
            filtered = []
            for item in candidates:
                match = True
                for param_name, param_val in params.items():
                    attr_name = param_name.split("_")[0]
                    if hasattr(item, attr_name) and getattr(item, attr_name) != param_val:
                        match = False
                        break
                if match:
                    filtered.append(item)
            return MockResult(filtered)
        return MockResult(candidates)


@pytest.fixture
def stage1_seeded_entities():
    actor = ResearchActor(
        id="actor_curie_01",
        display_name="Marie Curie",
        orcid="0000-0001-9876-5432",
        organization_id="org_sorbonne_01",
        is_anonymized=False,
    )
    actor.email = "marie.curie@radium-lab.fr"
    actor.user_account_id = "user_acc_curie_secret_999"

    project = ResearchProject(
        id="proj_radioactive_decay",
        slug="radioactive-decay-kinetics",
        title="Radioactive Decay Kinetics and Energy Invariance",
        description="Comprehensive derivation of exponential decay laws and dimensional validation.",
        owner_actor_id=actor.id,
        organization_id=actor.organization_id,
        visibility="public_preprint",
        is_frozen=True,
    )

    version_frozen = ResearchVersion(
        id="ver_curie_frozen_001",
        project_id=project.id,
        version_number=1,
        title="Decay Kinetics Formulation v1",
        content_hash="deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        publication_status="published",
        is_frozen=True,
    )

    var_n0 = Variable(
        id="var_n0_01",
        version_id=version_frozen.id,
        symbol="N_0",
        name="InitialQuantity",
        unit="dimensionless",
        domain="positive_real",
        latex_presentation=r"N_0",
    )

    var_lambda = Variable(
        id="var_lambda_02",
        version_id=version_frozen.id,
        symbol="lambda_decay",
        name="DecayConstant",
        unit="1 / second",
        domain="positive_real",
        latex_presentation=r"\lambda",
    )

    var_t = Variable(
        id="var_t_03",
        version_id=version_frozen.id,
        symbol="t",
        name="Time",
        unit="second",
        domain="positive_real",
        latex_presentation="t",
    )

    eq_decay = Equation(
        id="eq_decay_01",
        version_id=version_frozen.id,
        label="ExponentialDecayLaw",
        latex_raw=r"N(t) = N_0 e^{-\lambda t}",
        canonical_ast_json={
            "node_type": "binary_op",
            "op": "*",
            "left": {"node_type": "variable", "value": "N_0"},
            "right": {
                "node_type": "function_call",
                "func": "exp",
                "args": [
                    {
                        "node_type": "unary_op",
                        "op": "neg",
                        "left": {
                            "node_type": "binary_op",
                            "op": "*",
                            "left": {"node_type": "variable", "value": "lambda_decay"},
                            "right": {"node_type": "variable", "value": "t"},
                        },
                    }
                ],
            },
        },
        sympy_expr="N_0 * exp(-lambda_decay * t)",
    )

    val_run = ValidationRun(
        id="run_decay_001",
        version_id=version_frozen.id,
        status="completed",
        overall_state="PASS",
    )

    finding_l1 = ValidationFinding(
        id="find_l1_01",
        run_id=val_run.id,
        layer=1,
        target_entity_type="EQUATION",
        target_entity_id=eq_decay.id,
        job_id="job_decay_syntax_01",
        state="PASS",
        diagnostic_code="SYNTAX_SEMANTICS_VALIDATED",
        message="Layer 1 mathematical syntax and symbol-first mapping verified.",
        dimensions_verified=True,
        diagnostics={"complexity_depth": 5, "node_count": 8},
    )

    finding_l2 = ValidationFinding(
        id="find_l2_02",
        run_id=val_run.id,
        layer=2,
        target_entity_type="EQUATION",
        target_entity_id=eq_decay.id,
        job_id="job_decay_bound_02",
        state="PASS",
        diagnostic_code="ASYMPTOTIC_BOUNDS_VALIDATED",
        message="Layer 2 asymptotic limit t->inf converges to 0 without singularity.",
        dimensions_verified=True,
        diagnostics={"poles_detected": []},
    )

    finding_l3 = ValidationFinding(
        id="find_l3_03",
        run_id=val_run.id,
        layer=3,
        target_entity_type="EQUATION",
        target_entity_id=eq_decay.id,
        job_id="job_decay_dim_03",
        state="PASS",
        diagnostic_code="DIMENSIONAL_HOMOGENEITY_VERIFIED",
        message="Layer 3 Pint dimensional check: lambda * t is dimensionless, result is dimensionless.",
        dimensions_verified=True,
        diagnostics={"dimensionality": "dimensionless"},
    )

    return {
        "actor": actor,
        "project": project,
        "version_frozen": version_frozen,
        "variables": [var_n0, var_lambda, var_t],
        "equations": [eq_decay],
        "validation_run": val_run,
        "findings": [finding_l1, finding_l2, finding_l3],
    }


# ==============================================================================
# TIER 1: FRONTEND AST & VISUAL FLOW CONTRACTS
# ==============================================================================
def test_tier1_ast_and_visual_canvas_flow():
    """Tier 1: Verifies frontend AST construction, validation contracts, and static evaluation."""
    # Build kinetic energy AST: 0.5 * m * v^2
    ast = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.MUL,
        left=ExprNode(node_type=NodeType.CONSTANT, value=0.5),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.VARIABLE, value="m"),
            right=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.POW,
                left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
                right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
            ),
        ),
    )

    assert ast.node_type == NodeType.BINARY_OP
    assert ast.left.value == 0.5

    # Constant evaluation test
    const_sub = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.CONSTANT, value=10.0),
        right=ExprNode(node_type=NodeType.CONSTANT, value=5.5),
    )
    assert try_eval_constant_ast(const_sub) == 15.5

    # Function call evaluation test (sqrt(16) == 4.0)
    sqrt_node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[ExprNode(node_type=NodeType.CONSTANT, value=16.0)],
    )
    assert try_eval_constant_ast(sqrt_node) == 4.0

    # Negative sqrt returns None (prevents complex numbers)
    neg_sqrt = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[ExprNode(node_type=NodeType.CONSTANT, value=-16.0)],
    )
    assert try_eval_constant_ast(neg_sqrt) is None

    # Variable node returns None (cannot be statically evaluated to float)
    assert try_eval_constant_ast(ast) is None

    # Boolean values are strictly forbidden
    with pytest.raises(ValueError, match="Boolean values are forbidden"):
        ExprNode(node_type=NodeType.CONSTANT, value=True)


# ==============================================================================
# TIER 2: BACKEND DOMAIN, IDENTITY SPLIT & VERSION FREEZING CONTRACTS
# ==============================================================================
def test_tier2_backend_domain_and_version_immutability(stage1_seeded_entities):
    """Tier 2: Verifies entity relationships, identity split, and frozen snapshot contracts."""
    entities = stage1_seeded_entities
    actor = entities["actor"]
    project = entities["project"]
    ver = entities["version_frozen"]

    # Verify Identity Split
    assert actor.user_account_id is not None
    assert project.owner_actor_id == actor.id
    assert ver.is_frozen is True
    assert ver.publication_status == "published"

    # GDPR erasure preservation: nullifying user_account_id keeps scholarly actor
    actor.user_account_id = None
    actor.is_anonymized = True
    assert project.owner_actor_id == actor.id
    assert actor.display_name == "Marie Curie"


# ==============================================================================
# TIER 3: COMPUTE SANDBOX & RCE DISPATCHING / INGESTION CONTRACTS
# ==============================================================================
@pytest.mark.asyncio
async def test_tier3_compute_orchestration_contracts():
    """Tier 3: Verifies packaging JobBundle into Celery v2 envelope and finding taxonomy."""
    bundle = JobBundle(
        job_id="job_decay_test_100",
        version_id="ver_curie_frozen_001",
        target_entity_type="EQUATION",
        target_entity_id="eq_decay_01",
        expression_ast=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
            right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
        ),
        variables=[
            VariableSpec(symbol="t", name="Time", unit="second", domain="positive_real")
        ],
        units=[
            UnitSpec(name="second", symbol="s", dimensionality="[time]")
        ],
    )

    mock_redis = AsyncMock()
    with patch("app.modules.compute_orchestrator.dispatcher.get_redis_client", return_value=mock_redis):
        job_id = await dispatch_compute_job(bundle)
        assert job_id == "job_decay_test_100"
        mock_redis.lpush.assert_called_once()
        queue, raw_envelope = mock_redis.lpush.call_args[0]
        assert queue == "compute_tasks"

        envelope = json.loads(raw_envelope)
        assert envelope["headers"]["task"] == "worker.tasks.verify_equation_ast"
        assert envelope["headers"]["id"] == "job_decay_test_100"

    # Finding result schema verification (7-state canonical taxonomy)
    finding = FindingResult(
        job_id="job_decay_test_100",
        state=FindingState.PASS,
        diagnostic_code="VALIDATION_PASSED",
        message="Layer 1-3 validation passed cleanly",
        dimensions_verified=True,
        diagnostics=["All dimensions and boundaries verified"],
    )
    assert finding.state == FindingState.PASS
    assert finding.dimensions_verified is True


# ==============================================================================
# TIER 4: CRYPTOGRAPHIC RESEARCH ZIP EXPORT & OFFLINE VERIFICATION
# ==============================================================================
@pytest.mark.asyncio
async def test_tier4_cryptographic_export_and_offline_verification(stage1_seeded_entities):
    """Tier 4: Verifies export of frozen research and executes standalone verify_bundle.py."""
    entities = stage1_seeded_entities
    db = MockDbSession([
        entities["actor"],
        entities["project"],
        entities["version_frozen"],
        *entities["variables"],
        *entities["equations"],
        entities["validation_run"],
        *entities["findings"],
    ])

    zip_bytes = await generate_research_zip_bundle(
        version_id=entities["version_frozen"].id,
        db=db,
        current_actor_id=entities["actor"].id,
    )
    assert len(zip_bytes) > 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_file_path = tmp_path / "bundle.zip"
        zip_file_path.write_bytes(zip_bytes)

        # 1. Verify standard offline verification on intact ZIP archive
        extract_dir = tmp_path / "unpacked"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_file_path, "r") as z:
            z.extractall(extract_dir)

        script_path = extract_dir / "verify_bundle.py"
        assert script_path.exists()

        # Run verify_bundle.py on extracted directory
        res_dir = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(extract_dir),
            capture_output=True,
            text=True,
        )
        assert res_dir.returncode == 0
        assert "[PASS] All bundle verification checks passed successfully." in res_dir.stdout

        # Run verify_bundle.py in archive mode (--zip)
        res_zip = subprocess.run(
            [sys.executable, str(script_path), "--zip", str(zip_file_path)],
            cwd=str(extract_dir),
            capture_output=True,
            text=True,
        )
        assert res_zip.returncode == 0
        assert "[PASS] All bundle verification checks passed successfully." in res_zip.stdout

        # 2. Tampering detection: alter paper.md
        paper_file = extract_dir / "paper.md"
        paper_file.write_text(paper_file.read_text() + "\nTampered content.")
        res_tamper = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(extract_dir),
            capture_output=True,
            text=True,
        )
        assert res_tamper.returncode != 0
        assert "[FAIL]" in res_tamper.stdout

        # Restore paper.md
        with zipfile.ZipFile(zip_file_path, "r") as z:
            z.extract("paper.md", extract_dir)

        # 3. Untracked file detection: inject malicious script
        malicious_file = extract_dir / "malicious_script.sh"
        malicious_file.write_text("echo 'pwned'")
        res_untracked = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(extract_dir),
            capture_output=True,
            text=True,
        )
        assert res_untracked.returncode != 0
        assert "Untracked / undeclared file(s) detected in bundle" in res_untracked.stdout

        # 4. Anti-Poisoning check (FINDING-M8-02 remediation verification):
        # Even if attacker adds hash of malicious file to checksums.sha256,
        # verification MUST fail because manifest.json is the authoritative signed authority.
        checksums_file = extract_dir / "checksums.sha256"
        with open(checksums_file, "a") as f:
            f.write("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef  malicious_script.sh\n")

        res_poison = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(extract_dir),
            capture_output=True,
            text=True,
        )
        assert res_poison.returncode != 0
        assert "Untracked / undeclared file(s) listed in checksums.sha256" in res_poison.stdout


# ==============================================================================
# FULL DUAL-TRACK E2E LIFECYCLE TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_full_stage1_lifecycle_integration(stage1_seeded_entities):
    """End-to-end integration: AST -> Compute Layers 1-3 -> Frozen Snapshot -> Signed ZIP Export."""
    entities = stage1_seeded_entities
    db = MockDbSession([
        entities["actor"],
        entities["project"],
        entities["version_frozen"],
        *entities["variables"],
        *entities["equations"],
        entities["validation_run"],
        *entities["findings"],
    ])

    # 1. Author equation and validate AST
    eq = entities["equations"][0]
    ast = ExprNode.model_validate(eq.canonical_ast_json)
    assert ast.node_type == NodeType.BINARY_OP

    # 2. Export to Cryptographic ZIP
    zip_bytes = await generate_research_zip_bundle(
        version_id=entities["version_frozen"].id,
        db=db,
        current_actor_id=entities["actor"].id,
    )
    assert len(zip_bytes) > 0

    # 3. Read back and check zero PII in metadata
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        actor_data = json.loads(z.read("metadata/actor.json"))
        assert "email" not in actor_data
        assert "user_account_id" not in actor_data
        assert actor_data["display_name"] == "Marie Curie"

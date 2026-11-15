"""Open Research Cryptographic ZIP Export Engine.

Generates a zero-lock-in, tamper-evident cryptographic ZIP bundle containing:
- manifest.json: JSON-LD metadata, author ORCID, license, content SHA-256 table.
- checksums.sha256: Standard Linux sha256sum text format for all files in bundle.
- signature.json: Platform HMAC-SHA256 digital signature of canonical manifest.json.
- paper.md: Clean Markdown publication paper with equations, variables, findings, checksums.
- metadata/: project.json, version.json, actor.json (ZERO PII).
- math/: variables.json, units.json, equations/eq_{id}_{label}.json (canonical ExprNode ASTs).
- validation/: validation_report.json with findings across Layers 1-3.
- verify_bundle.py: Standalone zero-dependency offline verification script.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.research_core.models import (
    Equation,
    ResearchActor,
    ResearchProject,
    ResearchVersion,
    ValidationFinding,
    ValidationRun,
    Variable,
)

VERIFY_BUNDLE_SCRIPT_TEMPLATE = '''#!/usr/bin/env python3
"""Standalone Offline Verification Script for Open Research Cryptographic Bundle.

Zero external dependencies. Requires Python 3.8+.
Verifies:
1. File integrity via checksums.sha256 and manifest.json.
2. JSON-LD structure and platform digital signature (signature.json).
3. Zero PII guarantees in metadata/actor.json.
4. Mathematical AST validity in math/equations/.
"""

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

FORBIDDEN_PII_KEYS = {"email", "password", "hashed_password", "user_account_id"}
ALLOWED_NODE_TYPES = {"constant", "variable", "binary_op", "unary_op", "function_call"}
ALLOWED_OPERATORS = {"+", "-", "*", "/", "**", "neg"}
ALLOWED_FUNCTIONS = {"sqrt", "sin", "cos", "exp", "log"}


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_ast_node(node: dict, path: str = "root") -> None:
    if not isinstance(node, dict):
        raise ValueError(f"AST node at {path} must be a dictionary, got {type(node).__name__}")
    
    node_type = node.get("node_type")
    if node_type not in ALLOWED_NODE_TYPES:
        raise ValueError(f"Invalid node_type '{node_type}' at {path}")

    if node_type == "constant":
        val = node.get("value")
        if val is None or isinstance(val, bool):
            raise ValueError(f"Constant node at {path} has invalid value: {val}")
    elif node_type == "variable":
        val = node.get("value")
        if not isinstance(val, str) or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", val):
            raise ValueError(f"Variable node at {path} has invalid symbol: {val}")
    elif node_type == "unary_op":
        op = node.get("op")
        if op not in ALLOWED_OPERATORS:
            raise ValueError(f"Unary op at {path} has invalid op: {op}")
        if "left" not in node or not node["left"]:
            raise ValueError(f"Unary op at {path} missing 'left' operand")
        validate_ast_node(node["left"], f"{path}.left")
    elif node_type == "binary_op":
        op = node.get("op")
        if op not in ALLOWED_OPERATORS:
            raise ValueError(f"Binary op at {path} has invalid op: {op}")
        if "left" not in node or not node["left"]:
            raise ValueError(f"Binary op at {path} missing 'left' operand")
        if "right" not in node or not node["right"]:
            raise ValueError(f"Binary op at {path} missing 'right' operand")
        validate_ast_node(node["left"], f"{path}.left")
        validate_ast_node(node["right"], f"{path}.right")
    elif node_type == "function_call":
        func = node.get("func")
        if func not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Function call at {path} has invalid func: {func}")
        args = node.get("args")
        if not isinstance(args, list) or len(args) != 1:
            raise ValueError(f"Function call at {path} requires exactly 1 argument")
        validate_ast_node(args[0], f"{path}.args[0]")


def verify_bundle_directory(base_dir: Path, secret_key: str = None) -> bool:
    print(f"=== Verifying Open Research Bundle in: {base_dir.resolve()} ===")
    errors = []

    # 1. Verify checksums.sha256
    checksums_file = base_dir / "checksums.sha256"
    checksums_declared_files = set()
    if not checksums_file.exists():
        errors.append("Missing required file: checksums.sha256")
    else:
        print("[1/5] Checking file integrity against checksums.sha256...")
        with open(checksums_file, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"\\s+", line, maxsplit=1)
                if len(parts) != 2:
                    errors.append(f"Invalid format in checksums.sha256 line {line_no}: {line}")
                    continue
                expected_sha, rel_path = parts[0], parts[1].replace("\\\\", "/")
                checksums_declared_files.add(rel_path)
                target_file = base_dir / rel_path
                if not target_file.exists():
                    errors.append(f"File listed in checksums.sha256 not found: {rel_path}")
                    continue
                actual_sha = compute_sha256(target_file.read_bytes())
                if actual_sha != expected_sha:
                    errors.append(f"SHA-256 mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")
        if not errors:
            print("      All files in checksums.sha256 verified successfully.")

    # 2. Verify manifest.json and JSON-LD structure
    manifest_file = base_dir / "manifest.json"
    manifest_bytes = None
    manifest_files_set = set()
    if not manifest_file.exists():
        errors.append("Missing required file: manifest.json")
    else:
        print("[2/5] Validating JSON-LD manifest.json...")
        try:
            manifest_bytes = manifest_file.read_bytes()
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            if "@context" not in manifest:
                errors.append("manifest.json missing required '@context'")
            if manifest.get("@type") != "ResearchArtifactBundle":
                errors.append(f"manifest.json '@type' must be 'ResearchArtifactBundle', got: {manifest.get('@type')}")
            if manifest.get("license") != "CC-BY-4.0":
                errors.append(f"manifest.json 'license' must be 'CC-BY-4.0', got: {manifest.get('license')}")
            if "version_id" not in manifest or "project_slug" not in manifest:
                errors.append("manifest.json missing required metadata fields ('version_id', 'project_slug')")
            
            # Cross-check manifest files
            manifest_files = manifest.get("files", {})
            for rel_path, expected_sha in manifest_files.items():
                norm_rel_path = rel_path.replace("\\\\", "/")
                manifest_files_set.add(norm_rel_path)
                target_file = base_dir / norm_rel_path
                if not target_file.exists():
                    errors.append(f"File declared in manifest.json not found: {rel_path}")
                    continue
                actual_sha = compute_sha256(target_file.read_bytes())
                if actual_sha != expected_sha:
                    errors.append(f"Manifest SHA-256 mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")
            print("      JSON-LD manifest and file catalog verified.")
        except Exception as e:
            errors.append(f"Error parsing manifest.json: {e}")

    # Check for untracked / undeclared files (authoritative source is signed manifest)
    authoritative_declared_files = (
        set(manifest_files_set)
        | {"checksums.sha256", "manifest.json", "signature.json"}
    )
    untracked_in_checksums = checksums_declared_files - (
        set(manifest_files_set) | {"manifest.json", "signature.json"}
    )
    if untracked_in_checksums:
        errors.append(
            f"Untracked / undeclared file(s) listed in checksums.sha256: {sorted(untracked_in_checksums)}"
        )

    physical_files = {
        p.relative_to(base_dir).as_posix()
        for p in base_dir.rglob("*")
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(base_dir).parts)
        and p.name not in {"Thumbs.db", "desktop.ini"}
    }
    untracked_files = physical_files - authoritative_declared_files
    if untracked_files:
        errors.append(f"Untracked / undeclared file(s) detected in bundle: {sorted(untracked_files)}")

    # 3. Verify signature.json
    sig_file = base_dir / "signature.json"
    if not sig_file.exists():
        errors.append("Missing required file: signature.json")
    elif manifest_bytes is not None:
        print("[3/5] Checking platform cryptographic signature...")
        try:
            sig_data = json.loads(sig_file.read_text(encoding="utf-8"))
            manifest_sha = compute_sha256(manifest_bytes)
            if sig_data.get("manifest_sha256") != manifest_sha:
                errors.append(
                    f"Signature manifest SHA-256 mismatch: expected {sig_data.get('manifest_sha256')}, got {manifest_sha}"
                )
            if secret_key:
                expected_hmac = hmac.new(secret_key.encode("utf-8"), manifest_bytes, hashlib.sha256).hexdigest()
                if sig_data.get("signature") != expected_hmac:
                    errors.append("Platform HMAC-SHA256 signature verification FAILED with provided secret key.")
                else:
                    print("      Platform HMAC-SHA256 signature verified with secret key.")
            else:
                print("      Signature structure valid. (Pass --secret <key> to verify platform HMAC).")
        except Exception as e:
            errors.append(f"Error parsing signature.json: {e}")

    # 4. Verify Zero PII in metadata/actor.json
    actor_file = base_dir / "metadata" / "actor.json"
    if not actor_file.exists():
        errors.append("Missing required file: metadata/actor.json")
    else:
        print("[4/5] Checking zero-PII security guarantees in metadata/actor.json...")
        try:
            actor_data = json.loads(actor_file.read_text(encoding="utf-8"))
            for forbidden_key in FORBIDDEN_PII_KEYS:
                if forbidden_key in actor_data:
                    errors.append(f"PII LEAK DETECTED: '{forbidden_key}' found in metadata/actor.json")
            if not errors:
                print("      Zero PII verified: no email, password, or user account ID present.")
        except Exception as e:
            errors.append(f"Error checking metadata/actor.json: {e}")

    # 5. Verify Mathematical AST validity in math/equations/
    eq_dir = base_dir / "math" / "equations"
    print("[5/5] Validating mathematical ASTs in math/equations/...")
    if eq_dir.exists() and eq_dir.is_dir():
        eq_files = list(eq_dir.glob("*.json"))
        for eq_file in eq_files:
            try:
                eq_json = json.loads(eq_file.read_text(encoding="utf-8"))
                if "canonical_ast" not in eq_json:
                    errors.append(f"Equation {eq_file.name} missing 'canonical_ast'")
                else:
                    validate_ast_node(eq_json["canonical_ast"], path=eq_file.name)
            except Exception as e:
                errors.append(f"AST validation error in {eq_file.name}: {e}")
        print(f"      Verified {len(eq_files)} equation AST(s).")
    else:
        print("      No equation directory found or empty (skipping AST node checks).")

    print("=" * 60)
    if errors:
        print(f"[FAIL] Bundle verification FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("[PASS] All bundle verification checks passed successfully.")
        return True


def main():
    parser = argparse.ArgumentParser(description="Verify Open Research Cryptographic Bundle")
    parser.add_argument("path", nargs="?", default=".", help="Path to unzipped bundle directory")
    parser.add_argument("--zip", help="Path to bundle .zip archive to extract and verify")
    parser.add_argument("--secret", help="Platform HMAC secret key to verify signature")
    args = parser.parse_args()

    if args.zip:
        zip_path = Path(args.zip)
        if not zip_path.exists():
            print(f"Error: ZIP file not found: {zip_path}", file=sys.stderr)
            sys.exit(1)
        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"Extracting {zip_path} to temporary workspace...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)
            success = verify_bundle_directory(Path(tmp_dir), secret_key=args.secret)
    else:
        target_dir = Path(args.path)
        if not target_dir.exists():
            print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
            sys.exit(1)
        success = verify_bundle_directory(target_dir, secret_key=args.secret)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
'''


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sanitize_filename(label: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", label)


def _generate_markdown_paper(
    project: ResearchProject,
    version: ResearchVersion,
    actor_data: dict[str, Any],
    variables: list[Variable],
    equations: list[Equation],
    findings_data: list[dict[str, Any]],
    content_checksums: dict[str, str],
) -> str:
    created_date = (
        version.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if version.created_at
        else datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    orcid_text = f" (ORCID: [{actor_data['orcid']}](https://orcid.org/{actor_data['orcid']}))" if actor_data.get("orcid") else ""

    lines = [
        f"# {project.title} (v{version.version_number})",
        "",
        f"**Author**: {actor_data['display_name']}{orcid_text}  ",
        f"**Version**: {version.version_number} (`{version.id}`)  ",
        f"**Publication Status**: {version.publication_status}  ",
        "**License**: Creative Commons Attribution 4.0 International (CC-BY-4.0)  ",
        f"**Date**: {created_date}  ",
        "",
        "## Abstract & Project Description",
        "",
        project.description or "No project description provided.",
        "",
        "## Mathematical Formulations",
        "",
    ]

    if equations:
        for eq in equations:
            lines.extend([
                f"### {eq.label}",
                "",
                "$$",
                eq.latex_raw.strip(),
                "$$",
                "",
            ])
    else:
        lines.append("*No equations registered for this research version.*\n")

    lines.extend([
        "## Variables & Dimensional Units",
        "",
        "| Symbol | Name | Unit | Domain | LaTeX Presentation |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ])

    if variables:
        for var in variables:
            latex_disp = f"`{var.latex_presentation}`" if var.latex_presentation else f"`{var.symbol}`"
            lines.append(
                f"| `{var.symbol}` | {var.name} | `{var.unit}` | {var.domain} | {latex_disp} |"
            )
        lines.append("")
    else:
        lines.append("| — | *None declared* | — | — | — |\n")

    lines.extend([
        "## Validation Findings Summary",
        "",
        "| Layer | Target Entity | Job ID | State | Diagnostic Code | Summary |",
        "| :---: | :--- | :--- | :---: | :--- | :--- |",
    ])

    if findings_data:
        for f in findings_data:
            lines.append(
                f"| {f['layer']} | `{f['target_entity_type']}:{f['target_entity_id']}` | "
                f"`{f['job_id'][:8]}...` | **{f['state']}** | `{f['diagnostic_code']}` | {f['message']} |"
            )
        lines.append("")
    else:
        lines.append("| — | *No validation runs recorded* | — | — | — | — |\n")

    lines.extend([
        "## Integrity Checksums",
        "",
        "The following SHA-256 cryptographic hashes guarantee uncompromised reproducibility of this research bundle:",
        "",
        "| Relative File Path | SHA-256 Checksum |",
        "| :--- | :--- |",
    ])

    for file_path in sorted(content_checksums.keys()):
        lines.append(f"| `{file_path}` | `{content_checksums[file_path]}` |")

    lines.extend([
        "",
        "---",
        "*Generated by REALITY SCIENCE Open Research Platform. All claims cryptographically signed.*",
        "",
    ])

    return "\n".join(lines)


async def generate_research_zip_bundle(
    version_id: str,
    db: AsyncSession,
    current_actor_id: str | None = None,
) -> bytes:
    """Compiles and generates the complete, immutable Open Research Cryptographic ZIP bundle.

    Enforces:
    - version.is_frozen == True (raises ValueError with CANNOT_EXPORT_UNFROZEN_DRAFT).
    - Access control: private drafts can only be exported by the owner.
    - Zero PII: metadata/actor.json stripped of all private credentials/emails.
    - Standalone verification: verify_bundle.py included.
    - JSON-LD manifest and platform digital signature.
    """
    # 1. Fetch version
    stmt_v = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res_v = await db.execute(stmt_v)
    version = res_v.scalar_one_or_none()
    if not version:
        raise ValueError(f"Version not found: {version_id}")

    # 2. Strict freeze check
    if not version.is_frozen:
        raise ValueError("CANNOT_EXPORT_UNFROZEN_DRAFT: Research version must be frozen before export.")

    # 3. Fetch project
    stmt_p = select(ResearchProject).where(ResearchProject.id == version.project_id)
    res_p = await db.execute(stmt_p)
    project = res_p.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project not found for version: {version_id}")

    # 4. Access control check
    if project.visibility == "private_draft" and (
        not current_actor_id or current_actor_id != project.owner_actor_id
    ):
        raise PermissionError("ACCESS_DENIED: Private drafts can only be exported by the owner.")

    # 5. Fetch actor (owner)
    stmt_a = select(ResearchActor).where(ResearchActor.id == project.owner_actor_id)
    res_a = await db.execute(stmt_a)
    actor = res_a.scalar_one_or_none()

    # ZERO PII Guarantee
    actor_data: dict[str, Any] = {
        "id": actor.id if actor else project.owner_actor_id,
        "display_name": actor.display_name if actor else "Unknown Researcher",
        "orcid": actor.orcid if actor else None,
        "organization_id": actor.organization_id if actor else project.organization_id,
        "is_anonymized": actor.is_anonymized if actor else False,
    }
    # Double assertion: strip any accidental PII
    for forbidden in ("email", "password", "hashed_password", "user_account_id"):
        actor_data.pop(forbidden, None)

    # 6. Fetch Variables
    stmt_var = select(Variable).where(Variable.version_id == version.id).order_by(Variable.symbol)
    res_var = await db.execute(stmt_var)
    variables = list(res_var.scalars().all())

    # 7. Fetch Equations
    stmt_eq = select(Equation).where(Equation.version_id == version.id).order_by(Equation.created_at)
    res_eq = await db.execute(stmt_eq)
    equations = list(res_eq.scalars().all())

    # 8. Fetch Validation Runs & Findings
    stmt_runs = (
        select(ValidationRun)
        .where(ValidationRun.version_id == version.id)
        .order_by(ValidationRun.created_at.desc())
    )
    res_runs = await db.execute(stmt_runs)
    runs = list(res_runs.scalars().all())

    all_findings_flat: list[dict[str, Any]] = []
    runs_data: list[dict[str, Any]] = []
    for r in runs:
        stmt_f = (
            select(ValidationFinding)
            .where(ValidationFinding.run_id == r.id)
            .order_by(ValidationFinding.layer, ValidationFinding.created_at)
        )
        res_f = await db.execute(stmt_f)
        findings = list(res_f.scalars().all())
        findings_list = [
            {
                "id": f.id,
                "layer": f.layer,
                "target_entity_type": f.target_entity_type,
                "target_entity_id": f.target_entity_id,
                "job_id": f.job_id,
                "state": f.state,
                "diagnostic_code": f.diagnostic_code,
                "message": f.message,
                "symbolic_simplification": f.symbolic_simplification,
                "dimensions_verified": f.dimensions_verified,
                "diagnostics": f.diagnostics,
            }
            for f in findings
        ]
        all_findings_flat.extend(findings_list)
        runs_data.append({
            "id": r.id,
            "status": r.status,
            "overall_state": r.overall_state,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "findings": findings_list,
        })

    # Prepare bundle memory map: {relative_path: bytes}
    bundle_files: dict[str, bytes] = {}

    # Metadata files
    project_dict = {
        "id": project.id,
        "slug": project.slug,
        "title": project.title,
        "description": project.description,
        "owner_actor_id": project.owner_actor_id,
        "organization_id": project.organization_id,
        "visibility": project.visibility,
        "is_frozen": project.is_frozen,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }
    bundle_files["metadata/project.json"] = json.dumps(project_dict, indent=2, sort_keys=True).encode("utf-8")

    version_dict = {
        "id": version.id,
        "project_id": version.project_id,
        "version_number": version.version_number,
        "title": version.title,
        "content_hash": version.content_hash,
        "publication_status": version.publication_status,
        "is_frozen": version.is_frozen,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }
    bundle_files["metadata/version.json"] = json.dumps(version_dict, indent=2, sort_keys=True).encode("utf-8")
    bundle_files["metadata/actor.json"] = json.dumps(actor_data, indent=2, sort_keys=True).encode("utf-8")

    # Math files
    variables_dict = [
        {
            "id": v.id,
            "symbol": v.symbol,
            "name": v.name,
            "unit": v.unit,
            "domain": v.domain,
            "latex_presentation": v.latex_presentation,
        }
        for v in variables
    ]
    bundle_files["math/variables.json"] = json.dumps(variables_dict, indent=2, sort_keys=True).encode("utf-8")

    # Extract unique units
    seen_units = set()
    units_dict = []
    for v in variables:
        if v.unit not in seen_units:
            seen_units.add(v.unit)
            units_dict.append({
                "unit": v.unit,
                "symbols": [x.symbol for x in variables if x.unit == v.unit],
            })
    bundle_files["math/units.json"] = json.dumps(units_dict, indent=2, sort_keys=True).encode("utf-8")

    # Equations
    for eq in equations:
        clean_label = _sanitize_filename(eq.label)
        eq_filename = f"math/equations/eq_{eq.id}_{clean_label}.json"
        eq_dict = {
            "id": eq.id,
            "label": eq.label,
            "latex_raw": eq.latex_raw,
            "canonical_ast": eq.canonical_ast_json,
            "sympy_expr": eq.sympy_expr,
        }
        bundle_files[eq_filename] = json.dumps(eq_dict, indent=2, sort_keys=True).encode("utf-8")

    # Validation
    validation_dict = {
        "version_id": version.id,
        "runs": runs_data,
    }
    bundle_files["validation/validation_report.json"] = json.dumps(validation_dict, indent=2, sort_keys=True).encode("utf-8")

    # Verification script
    bundle_files["verify_bundle.py"] = VERIFY_BUNDLE_SCRIPT_TEMPLATE.strip().encode("utf-8") + b"\n"

    # Pre-compute checksums of content files to include in paper.md
    content_checksums: dict[str, str] = {}
    for path, data in bundle_files.items():
        content_checksums[path] = _compute_sha256(data)

    # Generate paper.md
    paper_md_text = _generate_markdown_paper(
        project=project,
        version=version,
        actor_data=actor_data,
        variables=variables,
        equations=equations,
        findings_data=all_findings_flat,
        content_checksums=content_checksums,
    )
    bundle_files["paper.md"] = paper_md_text.encode("utf-8")

    # Calculate complete catalog of files for manifest.json
    manifest_files_map: dict[str, str] = {}
    for path, data in bundle_files.items():
        manifest_files_map[path] = _compute_sha256(data)

    now_iso = datetime.now(UTC).isoformat()
    manifest_dict = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@type": "ResearchArtifactBundle",
        "version_id": version.id,
        "version_number": version.version_number,
        "project_slug": project.slug,
        "project_title": project.title,
        "created_at": now_iso,
        "license": "CC-BY-4.0",
        "author": {
            "name": actor_data["display_name"],
            "orcid": actor_data.get("orcid"),
        },
        "files": manifest_files_map,
    }
    manifest_bytes = json.dumps(manifest_dict, indent=2, sort_keys=True).encode("utf-8")
    bundle_files["manifest.json"] = manifest_bytes

    # Generate platform cryptographic signature over canonical manifest.json
    manifest_sha256 = _compute_sha256(manifest_bytes)
    platform_secret = settings.jwt_secret_key.encode("utf-8")
    hmac_signature = hmac.new(platform_secret, manifest_bytes, hashlib.sha256).hexdigest()

    signature_dict = {
        "algorithm": "HMAC-SHA256",
        "key_id": "platform-default",
        "signed_at": now_iso,
        "manifest_sha256": manifest_sha256,
        "signature": hmac_signature,
    }
    bundle_files["signature.json"] = json.dumps(signature_dict, indent=2, sort_keys=True).encode("utf-8")

    # Generate standard Linux checksums.sha256 for all bundle files except checksums.sha256
    checksum_lines: list[str] = []
    for rel_path in sorted(bundle_files.keys()):
        file_sha = _compute_sha256(bundle_files[rel_path])
        checksum_lines.append(f"{file_sha}  {rel_path}")

    checksums_bytes = ("\n".join(checksum_lines) + "\n").encode("utf-8")
    bundle_files["checksums.sha256"] = checksums_bytes

    # Pack into in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(bundle_files.keys()):
            zf.writestr(file_path, bundle_files[file_path])

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

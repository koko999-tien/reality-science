from difflib import unified_diff
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r"D:/Reality_Science")
EVIDENCE = ROOT / ".reality/evidence/2026-11-16-compute-queue"
FILES = [
    "backend/app/core/redis.py",
    "backend/app/modules/compute_orchestrator/errors.py",
    "backend/app/modules/compute_orchestrator/dispatcher.py",
    "backend/app/modules/compute_orchestrator/ingestion.py",
    "backend/app/modules/compute_orchestrator/service.py",
    "backend/app/modules/cluster_orchestrator/dispatcher.py",
    "backend/app/modules/reality_constraint_engine/router.py",
    "shared/shared/schemas/finding_result.py",
    "shared/shared/schemas/job_bundle.py",
    "worker/worker/celery_app.py",
    "worker/worker/tasks/compute_tasks.py",
    "backend/tests/unit/test_compute_orchestrator.py",
    "backend/tests/unit/test_compute_queue_boundary.py",
    "backend/tests/integration/test_stage4_final_e2e_integration.py",
    "backend/tests/integration/test_decision3_postgres_rls.py",
    "backend/tests/integration/test_compute_queue_live.py",
    "worker/tests/test_queue_contract.py",
    ".reality/evidence/2026-11-16-compute-queue/run_live.py",
    ".reality/evidence/2026-11-16-compute-queue/worker_bootstrap.py",
]

(EVIDENCE / "slice-files.json").write_text(json.dumps(FILES, indent=2), encoding="utf-8")
hashes = {}
for relative in FILES:
    path = ROOT / relative
    if path.is_file():
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
(EVIDENCE / "slice-sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")

patch_parts = []
for relative in FILES:
    current_path = ROOT / relative
    baseline_path = EVIDENCE / "baseline" / relative
    current = current_path.read_text(encoding="utf-8").splitlines(keepends=True) if current_path.is_file() else []
    baseline = baseline_path.read_text(encoding="utf-8").splitlines(keepends=True) if baseline_path.is_file() else []
    if baseline == current:
        continue
    patch_parts.extend(unified_diff(
        baseline,
        current,
        fromfile=f"a/{relative}" if baseline_path.is_file() else "/dev/null",
        tofile=f"b/{relative}" if current_path.is_file() else "/dev/null",
    ))
(EVIDENCE / "slice.patch").write_text("".join(patch_parts), encoding="utf-8", newline="\n")

print(json.dumps({"files": len(FILES), "hashed": len(hashes), "patch_bytes": (EVIDENCE / "slice.patch").stat().st_size}))

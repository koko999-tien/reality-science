"""Verify real failed-start cleanup, then the two additional ownership regressions.

Inject an exception in the marker verification call; never mutate the DB marker.
The independent core identity check and pg_ctl shutdown remain real.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys

BACKEND = Path("D:/Reality_Science/backend")
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from scripts import disposable_postgres as runner


def save_primary(manifest):
    (EVIDENCE / "instance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main():
    failure_evidence = EVIDENCE / "restart-failure-check"
    failure_evidence.mkdir(exist_ok=False)
    manifest = json.loads((EVIDENCE / "instance.json").read_text())
    path = failure_evidence / "instance.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    real_admin_connection = runner.admin_connection

    async def injected_marker_failure(target, database=None):
        # First perform the real online identity/marker check, so the injection
        # cannot hide an actual mismatch or select a different server.
        conn, _ = await real_admin_connection(target, database)
        await conn.close()
        raise RuntimeError("Injected post-start verification failure for cleanup regression")

    runner.admin_connection = injected_marker_failure
    try:
        try:
            runner.start_cluster(manifest, path, failure_evidence)
        except RuntimeError as exc:
            assert "Injected post-start" in str(exc), str(exc)
        else:
            raise AssertionError("Injected verification failure was not raised")
    finally:
        runner.admin_connection = real_admin_connection
        save_primary(manifest)
    runner.verify_clean_shutdown(manifest)
    assert manifest["stopped"] and manifest["lifecycle_state"] == "stopped"
    (failure_evidence / "result.json").write_text(json.dumps({
        "injected_marker_exception": True, "real_cluster_shutdown_verified": True,
        "db_marker_modified": False, "manifest": manifest,
    }, indent=2), encoding="utf-8")

    review_evidence = EVIDENCE / "review-live"
    review_evidence.mkdir(exist_ok=False)
    review_path = review_evidence / "instance.json"
    review_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    code = None
    try:
        runner.start_cluster(manifest, review_path, review_evidence)
        code = subprocess.run([
            sys.executable, "scripts/disposable_postgres.py", "test", "--evidence", str(review_evidence),
            "--log", "owner-transfer.log", "-vv", "--tb=short",
            "tests/integration/test_decision3_project_owner_transfer.py",
        ], cwd=BACKEND).returncode
    finally:
        # Always stop through the full online identity+DB marker check.
        stop_code = subprocess.run([
            sys.executable, "scripts/disposable_postgres.py", "stop", "--evidence", str(review_evidence)
        ], cwd=BACKEND).returncode
        manifest = json.loads(review_path.read_text())
        save_primary(manifest)
        runner.verify_clean_shutdown(manifest)
        (review_evidence / "result.json").write_text(json.dumps({
            "pytest_exit": code, "stop_exit": stop_code, "manifest": manifest,
            "control": runner.control_data(manifest),
        }, indent=2), encoding="utf-8")
        shutil.copyfile(Path(manifest["data"]).parent / "postgres.log", review_evidence / "postgres-server.log")
        assert stop_code == 0 and manifest["stopped"]
    return code


if __name__ == "__main__":
    raise SystemExit(main())

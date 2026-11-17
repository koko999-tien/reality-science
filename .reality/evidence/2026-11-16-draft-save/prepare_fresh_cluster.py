"""Recover identified old fixture cluster; provision a separate new synthetic one."""
import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

E = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("known_recovery", E.parent / "2026-11-17-review-fixes/recover_outer_timeout.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
recovery.E = E
recovery.RECOVERY = E / "migration-failure-recovery"
recovery.main()
old = json.loads((E / "instance.json").read_text())
(E / "live-api-01-instance.json").write_text(json.dumps(old, indent=2))
fresh = E / "fresh-cluster"
command = [sys.executable, str(E.parents[2] / "backend/scripts/disposable_postgres.py"), "init", "--evidence", str(fresh),
           "--bin", old["bin"], "--work", "C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-draft-save-pg-20261117"]
subprocess.run(command, check=True)
manifest = json.loads((fresh / "instance.json").read_text())
from scripts.disposable_postgres import admin_connection, stop_cluster
async def verify():
    conn, _ = await admin_connection(manifest)
    await conn.close()
asyncio.run(verify())
assert stop_cluster(manifest, fresh / "initial-stop.log") == 0
(fresh / "instance.json").write_text(json.dumps(manifest, indent=2))
(E / "instance.json").write_text(json.dumps(manifest, indent=2))
print("New task-owned cluster prepared and cleanly stopped")

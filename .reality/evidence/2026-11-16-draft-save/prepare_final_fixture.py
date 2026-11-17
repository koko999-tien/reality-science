"""New synthetic cluster for the final migration source; preserve prior fixtures."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys

E = Path(__file__).resolve().parent
ROOT = E.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.disposable_postgres import admin_connection, stop_cluster, verify_stopped_cluster

prior = json.loads((E / "instance.json").read_text())
verify_stopped_cluster(prior)
assert prior["system_id"] == "7708831198486449312"
with (E / "instance-before-review.json").open("x") as stream:
    json.dump(prior, stream, indent=2)
fresh = E / "final-fresh-cluster"
assert not fresh.exists()
subprocess.run([sys.executable, str(ROOT / "backend/scripts/disposable_postgres.py"), "init",
    "--evidence", str(fresh), "--bin", prior["bin"], "--work",
    "C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-draft-final-pg-20261117"], check=True)
path = fresh / "instance.json"
manifest = json.loads(path.read_text())
async def verify():
    conn, _ = await admin_connection(manifest)
    await conn.close()
asyncio.run(verify())
try:
    assert stop_cluster(manifest, fresh / "initial-stop.log") == 0
finally:
    path.write_text(json.dumps(manifest, indent=2))
assert manifest["stopped"]
(E / "instance.json").write_text(json.dumps(manifest, indent=2))
print("PASS: prior fixture retained; new identified cluster ready for final migration")

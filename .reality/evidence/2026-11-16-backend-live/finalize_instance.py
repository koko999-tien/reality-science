"""Recover only this task's stopped cluster, record identity, then stop cleanly.

No migrations, test writes, service changes or application configuration changes.
The absolute manifest, offline system ID and stale PID are checked before start.
"""

import asyncio
import json
from pathlib import Path
import socket
import subprocess
import sys

BACKEND = Path("D:/Reality_Science/backend")
EVIDENCE = BACKEND.parent / ".reality/evidence/2026-11-16-backend-live"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from scripts.disposable_postgres import admin_connection, environment
from tests.postgres_target import disposable_target, verify_disposable_connection


async def capture(manifest):
    admin, identity = await admin_connection(manifest)
    await admin.close()
    target = disposable_target(environment(manifest))
    engine = create_async_engine(target.url)
    try:
        async with engine.connect() as conn:
            report = {"cluster_identity": identity, "app_identity": await verify_disposable_connection(conn, target)}
            report["tables"] = [dict(row) for row in (await conn.execute(text(
                "SELECT relname,pg_get_userbyid(relowner) AS owner,relrowsecurity,relforcerowsecurity "
                "FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname"
            ))).mappings()]
            report["policies"] = [dict(row) for row in (await conn.execute(text(
                "SELECT tablename,policyname,cmd FROM pg_policies WHERE schemaname='public' ORDER BY tablename"
            ))).mappings()]
            report["revision"] = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            report["revision_column_size"] = (await conn.execute(text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_name='alembic_version' AND column_name='version_num'"
            ))).scalar_one()
            report["marker_writable"] = (await conn.execute(text(
                "SELECT has_table_privilege(current_user,'test_control.instance_identity','INSERT,UPDATE,DELETE')"
            ))).scalar_one()
        (EVIDENCE / "identity-and-policies.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        await engine.dispose()


def main():
    manifest_path = EVIDENCE / "instance.json"
    manifest = json.loads(manifest_path.read_text())
    data = Path(manifest["data"])
    binaries = Path(manifest["bin"])
    assert manifest["instance_id"] == "74caee9603bb4ea986e62cb223864982"
    assert manifest["system_id"] == "7708747722773675460"
    assert manifest["port"] == 60655 and manifest["postmaster_pid"] == 11164
    assert data.resolve() == Path("C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-postgres-83c0e945/data").resolve()
    assert binaries.resolve() == data.parent / "pgsql/bin"
    with socket.socket() as probe:
        probe.settimeout(1)
        assert probe.connect_ex(("127.0.0.1", manifest["port"])) != 0
    pid_rows = subprocess.check_output([
        "powershell.exe", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter 'ProcessId=11164' | Select-Object -ExpandProperty ProcessId"
    ], text=True).strip()
    assert not pid_rows
    control = subprocess.check_output([str(binaries / "pg_controldata.exe"), str(data)], text=True)
    assert f"Database system identifier:           {manifest['system_id']}" in control
    pid_lines = (data / "postmaster.pid").read_text().splitlines()
    assert int(pid_lines[0]) == manifest["postmaster_pid"]
    assert Path(pid_lines[1]).resolve() == data.resolve()
    with (EVIDENCE / "cleanup.log").open("w", encoding="utf-8") as log:
        log.write("Offline identity verified; old PID absent and port closed. Recovering task-owned cluster for clean shutdown.\n")
        log.flush()
        subprocess.run([str(binaries / "pg_ctl.exe"), "-D", str(data), "-l", str(data.parent / "postgres.log"),
                        "-w", "-t", "30", "start"], stdout=log, stderr=subprocess.STDOUT, check=True)
        try:
            asyncio.run(capture(manifest))
        finally:
            new_pid = int((data / "postmaster.pid").read_text().splitlines()[0])
            manifest["previous_postmaster_pid"] = manifest["postmaster_pid"]
            manifest["postmaster_pid"] = new_pid
            subprocess.run([str(binaries / "pg_ctl.exe"), "-D", str(data), "-m", "fast", "-w", "-t", "30", "stop"],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex(("127.0.0.1", manifest["port"])) != 0
        assert not (data / "postmaster.pid").exists()
        control = subprocess.check_output([str(binaries / "pg_controldata.exe"), str(data)], text=True)
        assert "Database cluster state:               shut down" in control
        log.write("Postmaster marker absent; port closed; cluster state shut down.\n")
        manifest.update(stopped=True, cleanup="Recovered verified task-owned cluster, captured read-only identity, fast shutdown verified")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print((EVIDENCE / "cleanup.log").read_text())


if __name__ == "__main__":
    main()

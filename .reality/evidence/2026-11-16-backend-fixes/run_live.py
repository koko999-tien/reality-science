"""Run this bounded disposable-DB verification and always stop its owned cluster."""

import asyncio
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

BACKEND = Path("D:/Reality_Science/backend")
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from scripts.disposable_postgres import admin_connection, control_data, environment
from tests.postgres_target import disposable_target, verify_disposable_connection


async def capture(name):
    manifest = json.loads((EVIDENCE / "instance.json").read_text())
    admin, identity = await admin_connection(manifest)
    await admin.close()
    target = disposable_target(environment(manifest))
    engine = create_async_engine(target.url)
    try:
        async with engine.connect() as conn:
            report = {"cluster_identity": identity,
                      "app_identity": await verify_disposable_connection(conn, target)}
            report["revision"] = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            report["policies"] = [dict(row) for row in (await conn.execute(text(
                "SELECT tablename,policyname,cmd,qual,with_check FROM pg_policies "
                "WHERE schemaname='public' ORDER BY tablename,cmd"
            ))).mappings()]
            report["tables"] = [dict(row) for row in (await conn.execute(text(
                "SELECT relname,pg_get_userbyid(relowner) AS owner,relrowsecurity,relforcerowsecurity "
                "FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname"
            ))).mappings()]
            report["marker_writable"] = (await conn.execute(text(
                "SELECT has_table_privilege(current_user,'test_control.instance_identity','INSERT,UPDATE,DELETE')"
            ))).scalar_one()
        (EVIDENCE / name).write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        await engine.dispose()


def run(action, *args):
    return subprocess.run([sys.executable, "scripts/disposable_postgres.py", action,
                           "--evidence", str(EVIDENCE), *args], cwd=BACKEND).returncode


def main():
    if (EVIDENCE / "live-all.log").exists() or (EVIDENCE / "pytest-live").exists():
        raise RuntimeError("Refusing to overwrite prior live evidence")
    codes = {}
    try:
        codes["start"] = run("start")
        if codes["start"]:
            return codes["start"]
        asyncio.run(capture("identity-before.json"))
        codes["migration"] = run("migrate", "--log", "migration-004.log")
        if codes["migration"]:
            return codes["migration"]
        asyncio.run(capture("identity-after.json"))
        codes["live"] = run("test", "--log", "live-all.log", "-vv", "--tb=short",
                            "--basetemp", str(EVIDENCE / "pytest-live"),
                            "tests/integration/test_decision3_postgres_rls.py")
        return codes["live"]
    finally:
        manifest = json.loads((EVIDENCE / "instance.json").read_text())
        if not manifest["stopped"]:
            codes["stop"] = run("stop")
        manifest = json.loads((EVIDENCE / "instance.json").read_text())
        data = Path(manifest["data"])
        ports = {manifest["port"]}
        for api_log in (EVIDENCE / "pytest-live").glob("*/api.log"):
            ports.update(int(port) for port in re.findall(
                r"Uvicorn running on http://127\.0\.0\.1:(\d+)", api_log.read_text()))
        listeners = {}
        for port in sorted(ports):
            with socket.socket() as sock:
                sock.settimeout(1)
                listeners[str(port)] = sock.connect_ex(("127.0.0.1", port)) == 0
        cleanup = {"codes": codes, "stopped": manifest["stopped"],
                   "postmaster_marker_exists": (data / "postmaster.pid").exists(),
                   "ports_accepting_connections": listeners, "control": control_data(manifest)}
        (EVIDENCE / "cleanup.json").write_text(json.dumps(cleanup, indent=2), encoding="utf-8")
        shutil.copyfile(data.parent / "postgres.log", EVIDENCE / "postgres-server.log")
        print(json.dumps(cleanup, indent=2))
        assert not cleanup["postmaster_marker_exists"] and manifest["stopped"]
        assert not any(listeners.values())


if __name__ == "__main__":
    raise SystemExit(main())

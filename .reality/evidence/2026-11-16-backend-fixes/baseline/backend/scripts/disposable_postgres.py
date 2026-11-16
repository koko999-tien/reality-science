"""Local-only PostgreSQL verification runner. Never attaches to an existing cluster.

Uses unpacked official binaries; no service registration or global installation.
Only the generated manifest may select a cluster for migration, tests or shutdown.
Loopback trust is restricted to two task roles; contains synthetic fixtures only.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

import asyncpg


BACKEND = Path(__file__).resolve().parents[1]


def execute(command, log, env=None):
    # A server grandchild can inherit a PIPE handle and keep communicate() open.
    # A real file allows pg_ctl to return while PostgreSQL stays detached.
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=BACKEND, env=env, text=True,
                                stdout=output, stderr=subprocess.STDOUT)
    print(log.read_text(encoding="utf-8"))
    print(f"exit={result.returncode}; log={log}")
    return result.returncode


def environment(manifest):
    env = os.environ.copy()
    url = f"postgresql+asyncpg://rs_test_app@127.0.0.1:{manifest['port']}/{manifest['database']}"
    env.update(REALITY_TEST_DATABASE_URL=url, REALITY_TEST_INSTANCE_ID=manifest["instance_id"],
               DATABASE_URL=url, ENVIRONMENT="test", PYTHONIOENCODING="utf-8")
    return env


async def admin_connection(manifest, database=None):
    conn = await asyncpg.connect(host="127.0.0.1", port=manifest["port"],
                                 user="rs_test_admin", database=database or manifest["database"], timeout=10)
    identity = await conn.fetchrow("""SELECT current_setting('data_directory') AS data,
        current_setting('cluster_name') AS cluster, system_identifier::text AS system_id
        FROM pg_control_system()""")
    if (Path(identity["data"]).resolve() != Path(manifest["data"]).resolve()
            or identity["cluster"] != manifest["database"]
            or (manifest.get("system_id") and identity["system_id"] != manifest["system_id"])):
        await conn.close()
        raise RuntimeError("Disposable cluster identity mismatch; refusing mutation")
    return conn, dict(identity)


async def provision(manifest):
    conn, identity = await admin_connection(manifest, "postgres")
    try:
        await conn.execute("CREATE ROLE rs_test_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT")
        await conn.execute(f'CREATE DATABASE "{manifest["database"]}" OWNER rs_test_admin')
    finally:
        await conn.close()
    conn, _ = await admin_connection(manifest)
    try:
        await conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        await conn.execute("CREATE SCHEMA test_control AUTHORIZATION rs_test_admin")
        await conn.execute("CREATE TABLE test_control.instance_identity(instance_id text PRIMARY KEY)")
        await conn.execute("INSERT INTO test_control.instance_identity VALUES ($1)", manifest["instance_id"])
        await conn.execute("GRANT USAGE ON SCHEMA test_control TO rs_test_app")
        await conn.execute("GRANT SELECT ON test_control.instance_identity TO rs_test_app")
        manifest.update(system_id=identity["system_id"], version=await conn.fetchval("SHOW server_version"))
    finally:
        await conn.close()


async def grant_app(manifest):
    conn, _ = await admin_connection(manifest)
    try:
        await conn.execute("GRANT USAGE ON SCHEMA public TO rs_test_app")
        await conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rs_test_app")
        await conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rs_test_app")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "resume-init", "migrate", "test", "stop"])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bin", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--log", default="pytest-live.log")
    args, pytest_args = parser.parse_known_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    manifest_path = args.evidence / "instance.json"
    if args.action == "init":
        if manifest_path.exists() or not args.work or not args.bin:
            parser.error("init requires fresh evidence manifest, --work and --bin")
        data = args.work.resolve() / "data"
        if data.exists():
            parser.error("Refusing existing data directory")
        token = uuid.uuid4().hex
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        manifest = dict(instance_id=token, database=f"rs_test_{token}", port=port,
                        data=str(data), bin=str(args.bin.resolve()), stopped=False)
        if execute([str(args.bin / "initdb.exe"), "-D", str(data), "-U", "rs_test_admin",
                    "--auth=trust", "--encoding=UTF8", "--locale=C"], args.evidence / "initdb.log"):
            return 1
        (data / "pg_hba.conf").write_text(
            "host all rs_test_admin 127.0.0.1/32 trust\n"
            f"host {manifest['database']} rs_test_app 127.0.0.1/32 trust\n"
            "host all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n", encoding="utf-8")
        with (data / "postgresql.conf").open("a", encoding="utf-8") as config:
            config.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\n"
                         f"cluster_name='{manifest['database']}'\nmax_connections=20\n"
                         "log_statement='none'\nlog_min_error_statement='panic'\n")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if execute([str(args.bin / "pg_ctl.exe"), "-D", str(data), "-l",
                    str(args.work / "postgres.log"), "-w", "-t", "30", "start"], args.evidence / "start.log"):
            return 1
        asyncio.run(provision(manifest))
        manifest["postmaster_pid"] = int((data / "postmaster.pid").read_text().splitlines()[0])
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.action == "resume-init":
        if manifest.get("system_id"):
            raise RuntimeError("Provisioning already completed")
        data = Path(manifest["data"])
        if execute([str(Path(manifest["bin"]) / "pg_ctl.exe"), "-D", str(data),
                    "-l", str(data.parent / "postgres.log"), "-w", "-t", "30", "start"],
                   args.evidence / "start-recovery.log"):
            return 1
        asyncio.run(provision(manifest))
        manifest["postmaster_pid"] = int((data / "postmaster.pid").read_text().splitlines()[0])
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0
    # Reconfirm cluster data directory + system identifier before any operation.
    async def check():
        conn, _ = await admin_connection(manifest)
        await conn.close()
    asyncio.run(check())
    if args.action == "migrate":
        env = environment(manifest)
        env["DATABASE_URL"] = env["DATABASE_URL"].replace("rs_test_app@", "rs_test_admin@")
        code = execute([sys.executable, "-m", "alembic", "upgrade", "head"],
                       args.evidence / args.log, env)
        if code == 0:
            asyncio.run(grant_app(manifest))
        return code
    if args.action == "test":
        return execute([sys.executable, "-m", "pytest", *pytest_args], args.evidence / args.log, environment(manifest))
    if args.action == "stop":
        current_pid = int((Path(manifest["data"]) / "postmaster.pid").read_text().splitlines()[0])
        if current_pid != manifest["postmaster_pid"]:
            raise RuntimeError("Postmaster PID changed; refusing shutdown")
        code = execute([str(Path(manifest["bin"]) / "pg_ctl.exe"), "-D", manifest["data"],
                        "-m", "fast", "-w", "-t", "30", "stop"], args.evidence / "stop.log")
        if code == 0:
            with socket.socket() as sock:
                sock.settimeout(1)
                assert sock.connect_ex(("127.0.0.1", manifest["port"])) != 0
            assert not (Path(manifest["data"]) / "postmaster.pid").exists()
            manifest["stopped"] = True
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return code


if __name__ == "__main__":
    raise SystemExit(main())

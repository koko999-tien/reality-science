"""Local-only PostgreSQL verification runner for clusters this task created.

Uses unpacked official binaries; no service registration or global installation.
Only the generated manifest may select a cluster for migration, tests or shutdown.
Loopback trust is restricted to two task roles; contains synthetic fixtures only.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import uuid

import asyncpg


BACKEND = Path(__file__).resolve().parents[1]


def validate_manifest(manifest):
    token = manifest.get("instance_id", "")
    port = manifest.get("port")
    if (not re.fullmatch(r"[a-f0-9]{32}", token)
            or manifest.get("database") != f"rs_test_{token}"
            or type(port) is not int or not 1024 <= port <= 65535 or port == 5432):
        raise RuntimeError("Invalid disposable cluster manifest")
    data = Path(manifest["data"])
    binaries = Path(manifest["bin"])
    if not data.is_absolute() or not binaries.is_absolute() or data.name != "data":
        raise RuntimeError("Disposable cluster paths must be explicit and absolute")


def control_data(manifest):
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    output = subprocess.check_output([
        str(Path(manifest["bin"]) / "pg_controldata.exe"), manifest["data"]
    ], text=True, env=env)
    values = dict(line.split(":", 1) for line in output.splitlines() if ":" in line)
    return {key.strip(): value.strip() for key, value in values.items()}


def verify_stopped_cluster(manifest):
    """No stale PID is trusted or removed; only a clean, identified cluster starts."""
    validate_manifest(manifest)
    data = Path(manifest["data"]).resolve()
    if not manifest.get("stopped") or not manifest.get("system_id"):
        raise RuntimeError("Restart requires a provisioned, cleanly stopped cluster")
    if (data / "postmaster.pid").exists():
        raise RuntimeError("Postmaster marker exists; refusing restart")
    control = control_data(manifest)
    if (control.get("Database system identifier") != manifest["system_id"]
            or control.get("Database cluster state") != "shut down"):
        raise RuntimeError("Offline cluster identity or clean shutdown check failed")
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    actual = {}
    for name in ("data_directory", "port", "listen_addresses", "cluster_name"):
        actual[name] = subprocess.check_output([
            str(Path(manifest["bin"]) / "postgres.exe"), "-D", str(data), "-C", name
        ], text=True, env=env).strip()
    if (Path(actual["data_directory"]).resolve() != data
            or actual["port"] != str(manifest["port"])
            or actual["listen_addresses"] != "127.0.0.1"
            or actual["cluster_name"] != manifest["database"]):
        raise RuntimeError("Disposable cluster configuration mismatch")
    # Binding is an availability check, never evidence of cluster ownership.
    with socket.socket() as sock:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", manifest["port"]))
    return {"data": str(data), "system_id": manifest["system_id"],
            "state": control["Database cluster state"], "config": actual,
            "postmaster_marker_absent": True, "port_available": True}


def current_postmaster(manifest):
    lines = (Path(manifest["data"]) / "postmaster.pid").read_text().splitlines()
    if (len(lines) < 8 or Path(lines[1]).resolve() != Path(manifest["data"]).resolve()
            or int(lines[3]) != manifest["port"] or lines[5] != "127.0.0.1"
            or lines[7].strip() != "ready" or int(lines[0]) <= 0):
        raise RuntimeError("Current postmaster marker does not match disposable target")
    return int(lines[0])


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


async def cluster_connection(manifest, database=None):
    """Verify the server identity even when a damaged DB marker needs cleanup."""
    validate_manifest(manifest)
    conn = await asyncpg.connect(host="127.0.0.1", port=manifest["port"],
                                 user="rs_test_admin", database=database or manifest["database"], timeout=10)
    try:
        identity = await conn.fetchrow("""SELECT current_setting('data_directory') AS data,
            current_setting('cluster_name') AS cluster, system_identifier::text AS system_id,
            current_database() AS database, current_user AS role,
            host(inet_server_addr()) AS host, inet_server_port() AS port
            FROM pg_control_system()""")
        if (Path(identity["data"]).resolve() != Path(manifest["data"]).resolve()
                or identity["cluster"] != manifest["database"]
                or identity["database"] != (database or manifest["database"])
                or identity["role"] != "rs_test_admin" or identity["host"] != "127.0.0.1"
                or identity["port"] != manifest["port"]
                or (manifest.get("system_id") and identity["system_id"] != manifest["system_id"])):
            raise RuntimeError("Disposable cluster identity mismatch; refusing mutation")
    except BaseException:
        await conn.close()
        raise
    return conn, dict(identity)


async def admin_connection(manifest, database=None):
    conn, identity = await cluster_connection(manifest, database)
    try:
        if manifest.get("system_id"):
            markers = await conn.fetch("SELECT instance_id FROM test_control.instance_identity")
            if [row["instance_id"] for row in markers] != [manifest["instance_id"]]:
                raise RuntimeError("Disposable database marker mismatch; refusing mutation")
    except BaseException:
        await conn.close()
        raise
    return conn, identity


def verify_clean_shutdown(manifest):
    if (Path(manifest["data"]) / "postmaster.pid").exists():
        raise RuntimeError("Postmaster marker survived shutdown")
    control = control_data(manifest)
    if (control.get("Database system identifier") != manifest["system_id"]
            or control.get("Database cluster state") != "shut down"):
        raise RuntimeError("Clean shutdown identity check failed")
    with socket.socket() as sock:
        sock.settimeout(1)
        if sock.connect_ex(("127.0.0.1", manifest["port"])) == 0:
            raise RuntimeError("Disposable port remains open after shutdown")


def stop_cluster(manifest, log):
    if current_postmaster(manifest) != manifest["postmaster_pid"]:
        raise RuntimeError("Postmaster PID changed; refusing shutdown")
    code = execute([str(Path(manifest["bin"]) / "pg_ctl.exe"), "-D", manifest["data"],
                    "-m", "fast", "-w", "-t", "30", "stop"], log)
    if code == 0:
        verify_clean_shutdown(manifest)
        manifest.update(stopped=True, lifecycle_state="stopped")
    return code


def start_cluster(manifest, manifest_path, evidence):
    offline = verify_stopped_cluster(manifest)
    (evidence / "restart-preflight.json").write_text(json.dumps(offline, indent=2), encoding="utf-8")
    data = Path(manifest["data"])

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    async def online(check_marker=True):
        connect = admin_connection if check_marker else cluster_connection
        conn, identity = await connect(manifest)
        await conn.close()
        return identity

    # Record uncertain launch state before spawning, never retain a historical PID
    # as the running PID if verification is interrupted.
    manifest.pop("postmaster_pid", None)
    manifest.pop("cleanup", None)
    manifest.update(stopped=False, lifecycle_state="starting")
    save()
    try:
        if execute([str(Path(manifest["bin"]) / "pg_ctl.exe"), "-D", str(data),
                    "-l", str(data.parent / "postgres.log"), "-w", "-t", "30", "start"],
                   evidence / "restart.log"):
            raise RuntimeError("PostgreSQL start failed; checking owned cluster cleanup")
        manifest.update(postmaster_pid=current_postmaster(manifest), lifecycle_state="verifying")
        save()
        identity = asyncio.run(online())
        manifest["lifecycle_state"] = "running"
        save()
        (evidence / "restart-identity.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
    except BaseException:
        manifest["lifecycle_state"] = "cleanup_required"
        save()
        try:
            if (data / "postmaster.pid").exists():
                # A DB marker failure blocks DB writes, but the independently
                # verified system ID/path/port identify our server for shutdown.
                asyncio.run(online(check_marker=False))
                manifest["postmaster_pid"] = current_postmaster(manifest)
                save()
                if stop_cluster(manifest, evidence / "restart-cleanup.log"):
                    raise RuntimeError("Restart cleanup shutdown failed")
            else:
                verify_clean_shutdown(manifest)
                manifest.update(stopped=True, lifecycle_state="stopped")
            save()
        except Exception as cleanup_error:
            save()
            raise RuntimeError("Restart verification failed; identity-checked cleanup requires recovery") from cleanup_error
        raise
    print("Restart verified: current system ID, data path, port and database marker match")
    return 0


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
    parser.add_argument("action", choices=["init", "resume-init", "start", "migrate", "test", "stop"])
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
    if args.action == "start":
        return start_cluster(manifest, manifest_path, args.evidence)
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
        code = stop_cluster(manifest, args.evidence / "stop.log")
        if code == 0:
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return code


if __name__ == "__main__":
    raise SystemExit(main())

"""One-time normal recovery of the identity-checked synthetic cluster after DDL failure."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

E = Path(__file__).resolve().parent
OUT = E / "live-api-02-recovery"
sys.path.insert(0, str(E.parents[2] / "backend"))
from scripts.disposable_postgres import (admin_connection, control_data, current_postmaster,
    execute, stop_cluster, validate_manifest, verify_clean_shutdown)


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2), encoding="utf-8")


async def online(manifest):
    conn, identity = await admin_connection(manifest)
    try:
        identity["schema_present"] = bool(await conn.fetchval("SELECT to_regclass('public.alembic_version')"))
        return identity
    finally:
        await conn.close()


def main():
    OUT.mkdir(exist_ok=False)
    path = E / "instance.json"
    manifest = json.loads(path.read_text())
    save("instance-before.json", manifest)
    validate_manifest(manifest)
    assert manifest["instance_id"] == "4058a17f49d64a9f9c0eb3b5b41a5966"
    assert manifest["system_id"] == "7708831198486449312" and manifest["port"] == 54761
    data = Path(manifest["data"]).resolve()
    assert data == Path("C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-draft-save-pg-20261117/data").resolve()
    state = control_data(manifest)
    save("control-before.json", state)
    assert state["Database system identifier"] == manifest["system_id"]
    try:
        identity = asyncio.run(online(manifest))
    except OSError:
        stale_pid = current_postmaster(manifest)
        script = (f"$p=@(Get-CimInstance Win32_Process | Where-Object {{ $_.Name -eq 'postgres.exe' -or $_.ProcessId -eq {stale_pid} }} | "
                  "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine)\nConvertTo-Json -InputObject $p -Depth 3")
        processes = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", script], text=True, timeout=20))
        save("processes-before.json", processes)
        assert processes == [], "Recovery refused while an existing PostgreSQL process or reused PID exists"
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", manifest["port"]))
        config = {key: subprocess.check_output([str(Path(manifest["bin"]) / "postgres.exe"), "-D", str(data), "-C", key], text=True).strip()
                  for key in ("data_directory", "port", "listen_addresses", "cluster_name")}
        save("config-before.json", config)
        assert Path(config["data_directory"]).resolve() == data and config["port"] == str(manifest["port"])
        assert config["listen_addresses"] == "127.0.0.1" and config["cluster_name"] == manifest["database"]
        assert execute([str(Path(manifest["bin"]) / "pg_ctl.exe"), "-D", str(data), "-l", str(OUT / "postgres.log"), "-w", "-t", "30", "start"], OUT / "start.log") == 0
        identity = asyncio.run(online(manifest))
    save("online-identity.json", identity)
    manifest["postmaster_pid"] = current_postmaster(manifest)
    assert stop_cluster(manifest, OUT / "stop.log") == 0
    verify_clean_shutdown(manifest)
    path.write_text(json.dumps(manifest, indent=2))
    save("result.json", {"status": "PASS", "clean_shutdown": True, "schema_rolled_back": not identity["schema_present"]})
    print("PASS: cluster identity, migration rollback and clean shutdown verified")


if __name__ == "__main__":
    main()

"""Recover only the identified synthetic cluster after the outer shell deadline.

Never remove a PID marker, reset WAL, initialize data, or kill a historical PID.
PostgreSQL performs its normal crash recovery after an offline identity check.
"""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
RECOVERY = E / 'outer-timeout-recovery'
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.disposable_postgres import (
    admin_connection, control_data, current_postmaster, execute, stop_cluster,
    validate_manifest, verify_clean_shutdown,
)


def save(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


async def online(manifest):
    conn, identity = await admin_connection(manifest)
    try:
        identity['revision'] = await conn.fetchval('SELECT version_num FROM alembic_version')
        assert identity['revision'] == '004_owner_only_dml'
        return identity
    finally:
        await conn.close()


def main():
    RECOVERY.mkdir(exist_ok=False)
    manifest_path = E / 'instance.json'
    manifest = json.loads(manifest_path.read_text())
    save(RECOVERY / 'instance-before.json', manifest)
    validate_manifest(manifest)
    assert manifest['instance_id'] == '74caee9603bb4ea986e62cb223864982'
    assert manifest['system_id'] == '7708747722773675460'
    assert manifest['port'] == 60655
    data = Path(manifest['data']).resolve()
    assert data == Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-postgres-83c0e945/data').resolve()
    marker = data / 'postmaster.pid'
    (RECOVERY / 'postmaster-before.txt').write_bytes(marker.read_bytes())
    stale_pid = current_postmaster(manifest)
    control = control_data(manifest)
    save(RECOVERY / 'control-before.json', control)
    assert control['Database system identifier'] == manifest['system_id']
    assert control['Database cluster state'] == 'in production'

    # A current process inventory is required; a historical PID is never killed.
    script = (
        "$ErrorActionPreference='Stop'\n"
        f"$p=@(Get-CimInstance Win32_Process | Where-Object {{ $_.Name -eq 'postgres.exe' -or $_.ProcessId -eq {stale_pid} }} | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine)\n"
        "ConvertTo-Json -InputObject $p -Depth 3"
    )
    output = subprocess.check_output([
        str(Path(os.environ['SYSTEMROOT']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
        '-NoProfile', '-NonInteractive', '-Command', script,
    ], text=True, timeout=20)
    processes = json.loads(output)
    save(RECOVERY / 'processes-before.json', processes)
    assert processes == [], 'A PostgreSQL process or reused PID exists; recovery refused'
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(('127.0.0.1', manifest['port']))

    config = {}
    for key in ('data_directory', 'port', 'listen_addresses', 'cluster_name'):
        config[key] = subprocess.check_output([
            str(Path(manifest['bin']) / 'postgres.exe'), '-D', str(data), '-C', key,
        ], text=True, timeout=10).strip()
    save(RECOVERY / 'config-before.json', config)
    assert Path(config['data_directory']).resolve() == data
    assert config['port'] == str(manifest['port'])
    assert config['listen_addresses'] == '127.0.0.1'
    assert config['cluster_name'] == manifest['database']

    manifest.pop('postmaster_pid', None)
    manifest.update(stopped=False, lifecycle_state='crash_recovery_starting')
    save(manifest_path, manifest)
    try:
        code = execute([
            str(Path(manifest['bin']) / 'pg_ctl.exe'), '-D', str(data),
            '-l', str(RECOVERY / 'postgres-recovery.log'), '-w', '-t', '30', 'start',
        ], RECOVERY / 'start.log')
        assert code == 0, 'PostgreSQL crash recovery failed'
        identity = asyncio.run(online(manifest))
        save(RECOVERY / 'online-identity.json', identity)
        manifest.update(postmaster_pid=current_postmaster(manifest), lifecycle_state='running')
        save(manifest_path, manifest)
    finally:
        # Online identity must match before we can request a shutdown.
        if marker.exists():
            identity = asyncio.run(online(manifest))
            save(RECOVERY / 'shutdown-identity.json', identity)
            manifest['postmaster_pid'] = current_postmaster(manifest)
            save(manifest_path, manifest)
            assert stop_cluster(manifest, RECOVERY / 'stop.log') == 0
        verify_clean_shutdown(manifest)
        manifest.update(stopped=True, lifecycle_state='stopped')
        save(manifest_path, manifest)
        save(RECOVERY / 'control-after.json', control_data(manifest))
    save(RECOVERY / 'result.json', {
        'status': 'PASS', 'system_id': manifest['system_id'],
        'stale_marker_handled_by_postgres': True, 'reset_or_manual_pid_deletion': False,
        'clean_shutdown_verified': True,
    })
    print('PASS: normal crash recovery, online identity, marker and clean shutdown verified')


if __name__ == '__main__':
    main()

"""Record local source identity, a bounded patch, and fresh cleanup inventory."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.disposable_postgres import control_data, verify_stopped_cluster


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2)


def main():
    baseline = json.loads((E / 'baseline-sha256.json').read_text())
    new = ['worker/tests/test_soft_deadline.py',
           'backend/tests/unit/test_live_queue_lifecycle.py',
           'backend/tests/integration/test_compute_soft_deadline_live.py']
    owned = [*baseline, *new]
    for name, expected in baseline.items():
        assert digest(E / 'baseline' / name) == expected
    patch = []
    for name in owned:
        old = (E / 'baseline' / name).read_text(encoding='utf-8').splitlines(keepends=True) if name in baseline else []
        current = (ROOT / name).read_text(encoding='utf-8').splitlines(keepends=True)
        assert old != current, name
        patch.append(f'diff --git a/{name} b/{name}\n')
        if name in new:
            patch.append('new file mode 100644\n')
        patch.extend(difflib.unified_diff(old, current, fromfile='a/' + name if old else '/dev/null', tofile='b/' + name))
    patch_path = E / 'owned-changes.patch'
    with patch_path.open('x', encoding='utf-8', newline='\n') as output:
        output.writelines(patch)
    checks = {}
    for label, command in [
        ('diff_check', ['git', 'diff', '--check']),
        ('patch_reverse_check', ['git', 'apply', '--reverse', '--check', '--whitespace=error', str(patch_path)]),
    ]:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=20)
        checks[label] = {'command': command, 'exit': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr}
    save(E / 'final-diff-check.json', checks)
    assert all(check['exit'] == 0 for check in checks.values())
    save(E / 'owned-source-sha256.json', {name: digest(ROOT / name) for name in owned})

    inputs = set()
    for name in ['backend/app', 'backend/tests', 'backend/scripts', 'worker/worker', 'worker/tests', 'shared']:
        inputs.update(path for path in (ROOT / name).rglob('*.py') if '.venv' not in path.parts)
    for folder in ['backend', 'worker', 'shared']:
        for name in ['pyproject.toml', 'requirements.lock', 'uv.lock']:
            path = ROOT / folder / name
            if path.exists():
                inputs.add(path)
    inputs.update(E.glob('*.py'))
    inputs.add(ROOT / '.reality/evidence/2026-11-16-compute-queue/run_live.py')
    save(E / 'verification-inputs-sha256.json', {
        path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(inputs)
    })

    manifest = json.loads((E / 'instance.json').read_text())
    offline = verify_stopped_cluster(manifest)
    ports = {manifest['port']}
    for path in E.glob('*-broker-identity.json'):
        ports.add(int(json.loads(path.read_text())['server']['tcp_port']))
    for path in E.glob('*-pytest/*/api.log'):
        ports.update(map(int, re.findall(r'Uvicorn running on http://127\.0\.0\.1:(\d+)', path.read_text())))
    listening = {}
    for port in sorted(ports):
        with socket.socket() as sock:
            sock.settimeout(.5)
            listening[str(port)] = sock.connect_ex(('127.0.0.1', port)) == 0
    script = (
        "$ErrorActionPreference='Stop'\n"
        "$p=@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(python|pythonw|postgres|pg_ctl|redis-server)\\.exe$' } | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine)\n"
        "ConvertTo-Json -InputObject $p -Depth 3"
    )
    raw = subprocess.check_output([
        str(Path(os.environ['SYSTEMROOT']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
        '-NoProfile', '-NonInteractive', '-Command', script,
    ], text=True, timeout=20)
    processes = json.loads(raw)
    # The inventory script itself and its Windows venv launcher may be present.
    relevant = [process for process in processes if not (
        process.get('CommandLine') and 'finalize_evidence.py' in process['CommandLine'])]
    task_markers = ['reality-postgres-83c0e945', 'reality-compute-queue-20261116',
                    'reality-worker-verification-20261116', '2026-11-17-review-fixes',
                    'D:\\Reality_Science\\backend']
    remaining = [process for process in relevant if any(
        marker.lower() in ((process.get('CommandLine') or '') + (process.get('ExecutablePath') or '')).lower()
        for marker in task_markers)]
    save(E / 'final-cleanup-inventory.json', {
        'time_utc': datetime.now(timezone.utc).isoformat(), 'offline_identity': offline,
        'postgres_control': control_data(manifest), 'ports_accepting': listening,
        'remaining_task_processes': remaining, 'other_relevant_process_count': len(relevant) - len(remaining),
        'method': 'Fresh CIM inventory, connect checks and offline cluster identity; no process killed',
    })
    assert remaining == []
    assert not any(listening.values())
    status = subprocess.check_output(['git', 'status', '--short', '--branch'], cwd=ROOT, text=True)
    (E / 'git-final.txt').write_text(status, encoding='utf-8')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == (E / 'head.txt').read_text().strip()
    save(E / 'final-identity.json', {
        'head': head, 'owned_files': len(owned), 'verification_inputs': len(inputs),
        'ports_checked': len(ports), 'baseline_hashes_unchanged': True,
        'diff_check': 'PASS', 'patch_reverse_check': 'PASS', 'cleanup': 'PASS',
    })
    print(f'PASS: {len(owned)} owned files; {len(inputs)} verification inputs; {len(ports)} closed ports; clean cluster')


if __name__ == '__main__':
    main()

"""Preserve the exact review input without touching existing evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
FILES = [
    'worker/worker/tasks/dimensional.py',
    'worker/worker/core/boundary_engine.py',
    'worker/worker/core/dimension_engine.py',
    'worker/worker/core/physical_invariants.py',
    'worker/worker/core/empirical_engine.py',
    'worker/worker/core/epistemic_engine.py',
    '.reality/evidence/2026-11-16-compute-queue/run_live.py',
]
if __name__ == '__main__':
    if (E / 'baseline').exists():
        raise RuntimeError('Baseline already recorded')
    hashes = {}
    for name in FILES:
        destination = E / 'baseline' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
        hashes[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    (E / 'baseline-sha256.json').write_text(json.dumps(hashes, indent=2))
    for name, args in [('git-before.txt', ['status', '--short', '--branch']),
                       ('head.txt', ['rev-parse', 'HEAD'])]:
        (E / name).write_bytes(subprocess.check_output(['git', *args], cwd=ROOT))
    print(f'Preserved {len(hashes)} input files')

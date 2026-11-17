"""Reuse checked lifecycle with this follow-up's evidence directory and bootstrap."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
OLD = ROOT / '.reality/evidence/2026-11-16-compute-queue'
sys.path.insert(0, str(ROOT / 'backend'))
spec = importlib.util.spec_from_file_location('live_queue_runner', OLD / 'run_live.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.E = E
if not (E / 'instance.json').exists():
    shutil.copy2(OLD / 'instance.json', E / 'instance.json')
mode = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else mode
if name != mode and (mode != 'live-normal' or not name.startswith('live-normal-retry')):
    raise ValueError('Only the normal lifecycle accepts a distinct retry evidence name')
if mode in {'soft-dimensions', 'soft-limit'}:
    os.environ['REALITY_TEST_SOFT_DEADLINE'] = mode.removeprefix('soft-')
    sys.argv = [sys.argv[0], name, 'tests/integration/test_compute_soft_deadline_live.py']
elif mode == 'live-normal':
    sys.argv = [sys.argv[0], name, 'tests/integration/test_compute_queue_live.py', '-k', 'not fault and not without_worker']
else:
    raise ValueError('Unknown evidence mode')
code = runner.main()
(E / (name + '-exit.json')).write_text(json.dumps({'mode': mode, 'name': name, 'exit': code}, indent=2))
raise SystemExit(code)

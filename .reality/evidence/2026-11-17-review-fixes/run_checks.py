"""Capture bounded default/targeted checks into new named evidence files."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
WORKER = Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-worker-verification-20261116/Scripts/python.exe')
mode, name, *selection = sys.argv[1:]
python = WORKER if mode == 'worker' else ROOT / 'backend/.venv/Scripts/python.exe'
cwd = ROOT / mode
env = os.environ.copy()
for key in ('REALITY_TEST_DATABASE_URL', 'REALITY_TEST_INSTANCE_ID', 'REALITY_TEST_QUEUE_INSTANCE'):
    env.pop(key, None)
env['PYTHONIOENCODING'] = 'utf-8'
command = [str(python), '-m', 'pytest', '-q', '--tb=short', *(selection or ['tests'])]
with (E / (name + '.log')).open('x', encoding='utf-8') as log:
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        code = process.wait(timeout=300)
    except BaseException:
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True, capture_output=True, timeout=30)
            process.wait(timeout=20)
        raise
(E / (name + '-command.json')).write_text(json.dumps({'command': command, 'cwd': str(cwd), 'exit': code}, indent=2))
print((E / (name + '.log')).read_text(encoding='utf-8'))
raise SystemExit(code)

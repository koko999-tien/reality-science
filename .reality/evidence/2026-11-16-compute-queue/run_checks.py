"""Capture commands/exits directly, without PowerShell's stderr formatting."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('D:/Reality_Science')
E=Path(__file__).resolve().parent
worker=Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-worker-verification-20261116/Scripts/python.exe')
env=os.environ.copy()
env.pop('REALITY_TEST_DATABASE_URL',None)
env.pop('REALITY_TEST_INSTANCE_ID',None)
env['PYTHONIOENCODING']='utf-8'
mode=sys.argv[1]
commands={
    'backend':([str(ROOT/'backend/.venv/Scripts/python.exe'),'-m','pytest','-q','--tb=short','tests'],ROOT/'backend'),
    'worker':([str(worker),'-m','pytest','-q','--tb=short','tests'],ROOT/'worker'),
    'shared':([str(worker),'-m','pytest','-q','--tb=short','tests'],ROOT/'shared'),
    'targeted':([str(ROOT/'backend/.venv/Scripts/python.exe'),'-m','pytest','-q','--tb=short',
                'tests/unit/test_compute_orchestrator.py','tests/unit/test_compute_queue_boundary.py',
                'tests/integration/test_stage4_final_e2e_integration.py'],ROOT/'backend'),
}
command,cwd=commands[mode]
name=sys.argv[2] if len(sys.argv)>2 else mode+'-default'
with (E/(name+'.log')).open('w',encoding='utf-8') as stream:
    code=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
(E/(name+'-command.json')).write_text(json.dumps({'command':command,'cwd':str(cwd),'exit':code},indent=2))
print((E/(name+'.log')).read_text(encoding='utf-8'))
raise SystemExit(code)

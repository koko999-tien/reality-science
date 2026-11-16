"""Preserve the intake files; download official Windows-compatible Redis runtime."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import urllib.request

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
FILES = [
    'backend/app/core/redis.py',
    'backend/app/modules/compute_orchestrator/dispatcher.py',
    'backend/app/modules/compute_orchestrator/ingestion.py',
    'backend/app/modules/cluster_orchestrator/dispatcher.py',
    'backend/app/modules/reality_constraint_engine/router.py',
    'shared/shared/schemas/job_bundle.py',
    'shared/shared/schemas/finding_result.py',
    'worker/worker/tasks/compute_tasks.py',
    'worker/worker/celery_app.py',
    'backend/tests/unit/test_compute_orchestrator.py',
    'backend/tests/integration/test_stage1_e2e_integration.py',
    'backend/tests/integration/test_stage4_final_e2e_integration.py',
    'backend/tests/integration/test_decision3_postgres_rls.py',
]
if (E/'baseline').exists():
    raise RuntimeError('Refusing to overwrite intake')
hashes = {}
for rel in FILES:
    source = ROOT / rel
    dest = E / 'baseline' / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    hashes[rel] = hashlib.sha256(source.read_bytes()).hexdigest()
(E/'baseline-sha256.json').write_text(json.dumps(hashes, indent=2))
for command, name in [(['git','status','--short','--branch'],'git-before.txt'),
                      (['git','rev-parse','HEAD'],'head.txt')]:
    (E/name).write_bytes(subprocess.check_output(command, cwd=ROOT))
shutil.copyfile(ROOT/'.reality/evidence/2026-11-16-backend-fixes/review-live/instance.json', E/'instance.json')
runtime = Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-compute-queue-20261116')
runtime.mkdir(exist_ok=False)
url = 'https://download.memurai.com/Memurai-Developer/8.2.0/Memurai-for-Redis-v8.2.0.msi'
installer = runtime/'Memurai-for-Redis-v8.2.0.msi'
urllib.request.urlretrieve(url, installer)
(E/'runtime-download.json').write_text(json.dumps({'url':url,'path':str(installer),
    'sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'bytes':installer.stat().st_size},indent=2))
print('Baseline saved; official Memurai Developer MSI downloaded, not installed')

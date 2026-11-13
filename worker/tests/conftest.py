import sys
from pathlib import Path

# Add shared and worker packages to sys.path for test execution
repo_root = Path(__file__).resolve().parent.parent.parent
shared_path = repo_root / "shared"
worker_path = repo_root / "worker"

if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

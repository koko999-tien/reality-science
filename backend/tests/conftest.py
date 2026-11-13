import sys
from pathlib import Path
import pytest

repo_root = Path(__file__).resolve().parent.parent.parent
backend_path = repo_root / "backend"
shared_path = repo_root / "shared"

if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

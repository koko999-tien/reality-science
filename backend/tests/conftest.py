import sys
from pathlib import Path
import pytest

repo_root = Path(__file__).resolve().parent.parent.parent
backend_path = repo_root / "backend"
shared_path = repo_root / "shared"
worker_path = repo_root / "worker"

if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from app.core.config import settings


@pytest.fixture(autouse=True)
def test_jwt_signing_key(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-jwt-signing-key-at-least-32-bytes")

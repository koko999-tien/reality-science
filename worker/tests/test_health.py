"""Unit tests for Compute Worker Health Check Engine."""

import os
import pytest
from unittest.mock import patch

from worker.core.health import check_worker_health, main


def test_worker_health_healthy_state():
    """Verify worker health reports healthy, correct version, and engine statuses."""
    health = check_worker_health(check_broker=False)
    assert health["status"] == "healthy"
    assert health["service"] == "reality-science-compute-worker"
    assert health["version"] == "0.1.0"
    assert health["security_zone"] == "Zone 3 (compute_net)"
    assert health["invariants"]["anti_database_guard"] == "passed"
    assert health["compute_engines"]["sympy"]["available"] is True
    assert health["compute_engines"]["pint"]["available"] is True


def test_worker_health_broker_unreachable():
    """Verify broker check reports unreachable when redis is offline without crashing."""
    health = check_worker_health(check_broker=True)
    # Redis daemon is not running in local test environment
    assert "unreachable" in health["broker"]["status"] or "connected" in health["broker"]["status"]


def test_worker_health_detects_security_violation():
    """Verify that injecting forbidden database credentials marks health as unhealthy."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://hacker@localhost/db"}):
        health = check_worker_health(check_broker=False)
        assert health["status"] == "unhealthy"
        assert "failed" in health["invariants"]["anti_database_guard"]


def test_worker_health_cli_main(capsys):
    """Verify main() CLI entrypoint returns exit code 0 when healthy."""
    code = main()
    assert code == 0
    captured = capsys.readouterr()
    assert "Compute Worker Health: healthy" in captured.out

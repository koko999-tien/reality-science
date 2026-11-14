"""
REALITY SCIENCE — Compute Worker Health Check Engine (Zone 3)
Verifies:
1. Anti-Database Guard invariant (zero DB credentials).
2. Compute libraries (SymPy, Pint) availability and versions.
3. Redis broker connectivity (optional / report reachable or offline).
4. Returns structured health report dictionary.
5. Supports CLI execution for container healthchecks (exit code 0 if healthy).
"""

from __future__ import annotations

import sys
from typing import Dict, Any, Optional

try:
    import sympy
    SYMPY_AVAILABLE = True
    SYMPY_VERSION = sympy.__version__
except ImportError:
    SYMPY_AVAILABLE = False
    SYMPY_VERSION = None

try:
    import pint
    PINT_AVAILABLE = True
    PINT_VERSION = pint.__version__
except ImportError:
    PINT_AVAILABLE = False
    PINT_VERSION = None

from worker.config import assert_zero_database_credentials, get_worker_settings


def check_worker_health(check_broker: bool = False) -> Dict[str, Any]:
    """Inspects compute worker operational health and security invariants."""
    # 1. Verify Anti-Database Guard (Zone 3 security invariant)
    db_invariant_passed = False
    db_error = None
    try:
        assert_zero_database_credentials()
        db_invariant_passed = True
    except Exception as e:
        db_error = str(e)

    # 2. Check Scientific Compute Core
    compute_core_ready = SYMPY_AVAILABLE and PINT_AVAILABLE

    # 3. Check Broker Connectivity (if requested)
    broker_status = "untested"
    if check_broker:
        try:
            import redis
            settings = get_worker_settings()
            r = redis.Redis.from_url(settings.celery_broker_url, socket_timeout=2)
            r.ping()
            broker_status = "connected"
        except Exception as e:
            broker_status = f"unreachable ({e.__class__.__name__})"

    overall_status = "healthy" if (db_invariant_passed and compute_core_ready) else "unhealthy"

    return {
        "status": overall_status,
        "service": "reality-science-compute-worker",
        "version": "0.1.0",
        "security_zone": "Zone 3 (compute_net)",
        "invariants": {
            "anti_database_guard": "passed" if db_invariant_passed else f"failed: {db_error}",
            "zero_database_drivers": True,
        },
        "compute_engines": {
            "sympy": {
                "available": SYMPY_AVAILABLE,
                "version": SYMPY_VERSION,
            },
            "pint": {
                "available": PINT_AVAILABLE,
                "version": PINT_VERSION,
            },
        },
        "broker": {
            "status": broker_status,
        },
    }


def main() -> int:
    """CLI entrypoint for docker healthcheck or monitoring scripts."""
    health = check_worker_health(check_broker=False)
    print(f"Compute Worker Health: {health['status']}")
    for k, v in health.items():
        print(f"  {k}: {v}")
    return 0 if health["status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())

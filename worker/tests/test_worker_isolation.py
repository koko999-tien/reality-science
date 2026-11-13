import importlib
import os
import re
import socket
import pytest


def test_no_database_env_vars():
    """Assert zero database connection variables exist in worker environment."""
    forbidden_pattern = re.compile(  # forbidden pattern check
        r"(POSTGRES|DATABASE_URL|PGUSER|PGPASSWORD|PGDATABASE)", re.IGNORECASE  # forbidden keys check
    )
    violations = [k for k in os.environ.keys() if forbidden_pattern.search(k)]
    assert not violations, f"Database variables leaked to worker: {violations}"


def test_no_database_drivers_installed():
    """Assert forbidden database drivers are not importable in worker environment."""
    forbidden_drivers = ["asyncpg", "psycopg", "psycopg2", "sqlite3"]
    for forbidden_driver in forbidden_drivers:
        with pytest.raises(ImportError):
            importlib.import_module(forbidden_driver)


def test_network_isolation_to_postgres():
    """Assert worker cannot resolve or connect to postgres:5432."""
    with pytest.raises((socket.gaierror, socket.timeout, ConnectionRefusedError, OSError)):
        s = socket.create_connection(("postgres", 5432), timeout=0.5)
        s.close()

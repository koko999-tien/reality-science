"""
REALITY SCIENCE — Worker Security Isolation Unit Tests (Zone 3)
Approved Decision 2 (ADR-002: Private Scientific Compute Infrastructure)
Mandate: Strict Zero-Database Invariant. Zero database credentials or drivers.
"""

import ast
import importlib
import os
import socket
from pathlib import Path
from typing import List, Set, Tuple
import pytest

from worker.config import (
    FORBIDDEN_ENV_PATTERNS,
    assert_zero_database_credentials,
)

# Third-party database drivers and ORMs forbidden in worker container
FORBIDDEN_THIRD_PARTY_DRIVERS = [
    "asyncpg",  # forbidden driver check
    "psycopg",  # forbidden driver check
    "psycopg2",  # forbidden driver check
    "sqlalchemy",  # forbidden driver check
    "databases",  # forbidden driver check
    "mysqlclient",  # forbidden driver check
    "pymysql",  # forbidden driver check
    "cx_Oracle",  # forbidden driver check
    "pymongo",  # forbidden driver check
]

# Prohibited database modules forbidden from being imported by worker code
FORBIDDEN_SQL_IMPORT_MODULES: Set[str] = {
    "sqlite3",  # forbidden module check
    "sqlite",  # forbidden module check
    "psycopg",  # forbidden module check
    "psycopg2",  # forbidden module check
    "asyncpg",  # forbidden module check
    "sqlalchemy",  # forbidden module check
    "databases",  # forbidden module check
    "mysql",  # forbidden module check
    "pymysql",  # forbidden module check
    "cx_Oracle",  # forbidden module check
    "pymongo",  # forbidden module check
    "tortoise",  # forbidden module check
    "peewee",  # forbidden module check
    "ormar",  # forbidden module check
    "sqlmodel",  # forbidden module check
}


def test_no_database_env_vars():
    """Assert zero database connection variables exist in worker environment."""
    violations = []
    for key in os.environ.keys():
        for pattern in FORBIDDEN_ENV_PATTERNS:
            if pattern.match(key):
                violations.append(key)
                break
    assert not violations, f"Database variables leaked to worker: {violations}"
    # Verify pre-flight guard runs cleanly without exception in this environment
    assert_zero_database_credentials()


def test_no_database_drivers_installed():
    """Assert forbidden third-party database drivers are not importable in worker environment.

    Note: Standard library 'sqlite3' is excluded from ImportError assertions because it is
    bundled with CPython. Instead, worker code usage of sqlite3 is strictly banned via
    AST static analysis in test_no_database_imports_in_worker_code().
    """
    for forbidden_driver in FORBIDDEN_THIRD_PARTY_DRIVERS:
        with pytest.raises(ImportError):
            importlib.import_module(forbidden_driver)


def test_no_database_imports_in_worker_code():
    """AST static analysis: assert worker source code NEVER imports sqlite3 or any SQL package."""
    # Resolve worker source directory
    file_path = Path(__file__).resolve()
    worker_root = None
    for p in [file_path.parent.parent, file_path.parent.parent.parent, file_path.parent.parent.parent.parent]:
        candidate = p / "worker"
        if candidate.exists() and (candidate / "worker").exists():
            worker_root = candidate / "worker"
            break
        if candidate.exists() and (candidate / "tasks").exists():
            worker_root = candidate
            break

    assert worker_root and worker_root.exists(), f"Worker source directory not found relative to {file_path}"

    violations: List[Tuple[str, int, str]] = []

    for py_file in worker_root.rglob("*.py"):
        if "__pycache__" in str(py_file) or "tests" in str(py_file):
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
        except SyntaxError as e:
            pytest.fail(f"Syntax error parsing {py_file}: {e}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(".")[0].lower()
                    if root_module in FORBIDDEN_SQL_IMPORT_MODULES:
                        violations.append((str(py_file.name), node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_module = node.module.split(".")[0].lower()
                    if root_module in FORBIDDEN_SQL_IMPORT_MODULES:
                        violations.append((str(py_file.name), node.lineno, node.module))

    assert not violations, (
        f"Forbidden database modules imported in worker code: {violations}. "
        "Compute workers must evaluate in-memory ASTs with zero direct SQL/database access!"
    )


def test_anti_database_guard_rejects_alternate_keys():
    """Assert that assert_zero_database_credentials() blocks alternate database keys."""
    forbidden_alternate_keys = [
        "DATABASE_HOST",  # forbidden key check
        "DATABASE_PORT",  # forbidden key check
        "DATABASE_NAME",  # forbidden key check
        "DATABASE_URL",  # forbidden key check
        "SQL_USER",  # forbidden key check
        "SQL_PASSWORD",  # forbidden key check
        "DB_PASSWORD",  # forbidden key check
        "DB_HOST",  # forbidden key check
        "DB_USER",  # forbidden key check
        "SQLALCHEMY_DATABASE_URI",  # forbidden key check
        "MYSQL_PWD",  # forbidden key check
        "POSTGRES_PASSWORD",  # forbidden key check
        "PGHOST",  # forbidden key check
        "PGPORT",  # forbidden key check
        "PGUSER",  # forbidden key check
        "PGDATABASE",  # forbidden key check
    ]

    for key in forbidden_alternate_keys:
        orig_val = os.environ.get(key)
        try:
            os.environ[key] = "test_injection_value"
            with pytest.raises(RuntimeError) as exc_info:
                assert_zero_database_credentials()
            assert "FATAL SECURITY VIOLATION" in str(exc_info.value)
            assert key in str(exc_info.value)
        finally:
            if orig_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = orig_val


def test_network_isolation_to_postgres():
    """Assert worker cannot resolve or connect to postgres:5432."""
    with pytest.raises((socket.gaierror, socket.timeout, ConnectionRefusedError, OSError)):
        s = socket.create_connection(("postgres", 5432), timeout=0.5)
        s.close()

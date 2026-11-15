import sys
import subprocess
from pathlib import Path
import pytest


def test_offline_alembic_ddl_contains_stage1_contracts():
    """Validates Alembic offline SQL generation outputs Stage 1 DDL (tables and RLS policies)."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True,
        text=True,
        check=True,
        cwd=backend_dir,
    )
    sql = res.stdout

    # 1. Verify tables creation
    assert "CREATE TABLE equations" in sql
    assert "CREATE TABLE variables" in sql
    assert "CREATE TABLE validation_runs" in sql
    assert "CREATE TABLE validation_findings" in sql

    # 2. Verify foreign keys
    assert "FOREIGN KEY(version_id) REFERENCES research_versions (id) ON DELETE CASCADE" in sql
    assert "FOREIGN KEY(run_id) REFERENCES validation_runs (id) ON DELETE CASCADE" in sql

    # 3. Verify Row-Level Security enablement and enforcement
    assert "ALTER TABLE equations ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE equations FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_equations ON equations" in sql

    assert "ALTER TABLE variables ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE variables FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_variables ON variables" in sql

    assert "ALTER TABLE validation_runs ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE validation_runs FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_validation_runs ON validation_runs" in sql

    assert "ALTER TABLE validation_findings ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE validation_findings FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_validation_findings ON validation_findings" in sql

    # 4. Verify RLS policy references actor context and project visibility
    assert "rls_equations" in sql
    assert "rls_validation_findings" in sql
    assert "app.current_actor_id" in sql
    assert "public_preprint" in sql

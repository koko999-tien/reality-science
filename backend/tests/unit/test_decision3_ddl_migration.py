import sys
import subprocess
from pathlib import Path
import pytest


def test_offline_alembic_ddl_contains_decision3_contracts():
    """Validates Alembic offline SQL generation outputs all Decision 3 DDL without requiring a live DB."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True,
        text=True,
        check=True,
        cwd=backend_dir,
    )
    sql = res.stdout

    # 1. Identity split & right to erasure
    assert "CREATE TABLE user_accounts" in sql
    assert "CREATE TABLE research_actors" in sql
    assert "FOREIGN KEY(user_account_id) REFERENCES user_accounts (id) ON DELETE SET NULL" in sql

    # 2. Project visibility check constraint & organization_id
    assert "CREATE TABLE research_projects" in sql
    assert "organization_id" in sql
    assert "ck_project_visibility" in sql or "visibility IN ('private_draft', 'public_preprint')" in sql

    # 3. Research versions and snapshot freeze trigger
    assert "CREATE TABLE research_versions" in sql
    assert "trg_freeze_research_versions" in sql
    assert "CANNOT_MODIFY_FROZEN_VERSION" in sql

    # 4. Row Level Security policies
    assert "ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE research_projects FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_research_projects ON research_projects" in sql
    assert "app.current_actor_id" in sql
    assert "ALTER TABLE research_versions ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_research_versions ON research_versions" in sql

import subprocess
import sys
from pathlib import Path


def test_offline_alembic_ddl_contains_stage3_contracts():
    """Validates Alembic offline SQL generation outputs Stage 3 DDL (claims, claim_relations, and RLS policies)."""
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
    assert "CREATE TABLE claims" in sql
    assert "CREATE TABLE claim_relations" in sql

    # 2. Verify foreign keys
    assert "FOREIGN KEY(version_id) REFERENCES research_versions (id) ON DELETE CASCADE" in sql
    assert "FOREIGN KEY(source_claim_id) REFERENCES claims (id) ON DELETE CASCADE" in sql
    assert "FOREIGN KEY(target_claim_id) REFERENCES claims (id) ON DELETE CASCADE" in sql

    # 3. Verify Row-Level Security enablement and enforcement
    assert "ALTER TABLE claims ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE claims FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_claims ON claims" in sql

    assert "ALTER TABLE claim_relations ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE claim_relations FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY rls_claim_relations ON claim_relations" in sql

    # 4. Verify RLS policy references actor context and project visibility
    assert "rls_claims" in sql
    assert "rls_claim_relations" in sql
    assert "app.current_actor_id" in sql
    assert "public_preprint" in sql

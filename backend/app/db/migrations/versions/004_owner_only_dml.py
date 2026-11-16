"""Separate read visibility from owner-only project mutations.

Revision ID: 004_owner_only_dml
Revises: 003_stage3_claims_and_epistemic_logic

Master Brief section5 makes public preprints read-only. The earlier FOR ALL
policy's visibility predicate also authorized DELETE and the old UPDATE row.
Keep its SELECT semantics, but check ownership for both sides of every UPDATE.
"""

from alembic import op


revision = "004_owner_only_dml"
down_revision = "003_stage3_claims_and_epistemic_logic"
branch_labels = None
depends_on = None

TABLES = (
    "research_projects", "research_versions", "equations", "variables",
    "claims", "claim_relations", "validation_runs", "validation_findings",
)


def predicates(table: str) -> tuple[str, str]:
    prefix = "" if table == "research_projects" else "p."
    owner = f"{prefix}owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')"
    visible = f"""{prefix}visibility = 'public_preprint' OR {owner} OR (
        {prefix}organization_id IS NOT NULL AND
        {prefix}organization_id = NULLIF(current_setting('app.current_org_id', true), '')
    )"""
    if table == "research_projects":
        return visible, owner
    if table == "research_versions":
        parent = "research_projects p"
        link = "p.id = research_versions.project_id"
    elif table == "validation_findings":
        parent = """validation_runs r
            JOIN research_versions v ON v.id = r.version_id
            JOIN research_projects p ON p.id = v.project_id"""
        link = "r.id = validation_findings.run_id"
    else:
        parent = "research_versions v JOIN research_projects p ON p.id = v.project_id"
        link = f"v.id = {table}.version_id"
    return tuple(
        f"EXISTS (SELECT 1 FROM {parent} WHERE {link} AND ({condition}))"
        for condition in (visible, owner)
    )


def upgrade() -> None:
    for table in TABLES:
        visible, owner = predicates(table)
        op.execute(f"DROP POLICY rls_{table} ON {table}")
        op.execute(f"CREATE POLICY rls_{table}_select ON {table} FOR SELECT USING ({visible})")
        op.execute(f"CREATE POLICY rls_{table}_insert ON {table} FOR INSERT WITH CHECK ({owner})")
        op.execute(
            f"CREATE POLICY rls_{table}_update ON {table} FOR UPDATE "
            f"USING ({owner}) WITH CHECK ({owner})"
        )
        op.execute(f"CREATE POLICY rls_{table}_delete ON {table} FOR DELETE USING ({owner})")
        # ENABLE/FORCE RLS from migrations001-003 remain in force.


def downgrade() -> None:
    for table in reversed(TABLES):
        visible, owner = predicates(table)
        for command in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY rls_{table}_{command} ON {table}")
        op.execute(
            f"CREATE POLICY rls_{table} ON {table} FOR ALL "
            f"USING ({visible}) WITH CHECK ({owner})"
        )

"""Initial database schema with IAM, Research Core, and RLS metadata

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-13 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. User Accounts table (PII isolated)
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2. Research Actors table (Pseudonymous research persona)
    op.create_table(
        "research_actors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_account_id", sa.String(36), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("orcid", sa.String(19), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("is_anonymized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. Research Projects
    op.create_table(
        "research_projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_actor_id", sa.String(36), sa.ForeignKey("research_actors.id"), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="private_draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("visibility IN ('private_draft', 'public_preprint')", name="ck_project_visibility"),
    )

    # 4. Research Versions table
    op.create_table(
        "research_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("publication_status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 5. Freeze Trigger DDL
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_freeze_research_versions()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.is_frozen = TRUE THEN
            RAISE EXCEPTION 'CANNOT_MODIFY_FROZEN_VERSION: Research version % is frozen and immutable.', OLD.id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_freeze_research_versions
    BEFORE UPDATE OR DELETE ON research_versions
    FOR EACH ROW
    EXECUTE FUNCTION fn_freeze_research_versions();
    """)

    # 6. Row-Level Security (RLS) DDL
    op.execute("ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE research_projects FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_research_projects ON research_projects
    FOR ALL
    USING (
        visibility = 'public_preprint'
        OR owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        OR (
            organization_id IS NOT NULL 
            AND organization_id = NULLIF(current_setting('app.current_org_id', true), '')
        )
    )
    WITH CHECK (
        owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
    );
    """)

    op.execute("ALTER TABLE research_versions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE research_versions FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_research_versions ON research_versions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_projects p
            WHERE p.id = research_versions.project_id
            AND (
                p.visibility = 'public_preprint'
                OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
                OR (
                    p.organization_id IS NOT NULL 
                    AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')
                )
            )
        )
    );
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_freeze_research_versions ON research_versions;")
    op.execute("DROP FUNCTION IF EXISTS fn_freeze_research_versions();")
    op.drop_table("research_versions")
    op.drop_table("research_projects")
    op.drop_table("research_actors")
    op.drop_table("user_accounts")

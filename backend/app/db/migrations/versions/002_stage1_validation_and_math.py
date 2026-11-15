"""Stage 1 Validation and Math Schema: equations, variables, validation_runs, validation_findings with RLS

Revision ID: 002_stage1_validation_and_math
Revises: 001_initial_schema
Create Date: 2026-11-15 03:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_stage1_validation_and_math"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Equations table
    op.create_table(
        "equations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(36),
            sa.ForeignKey("research_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("latex_raw", sa.Text(), nullable=False),
        sa.Column("canonical_ast_json", sa.JSON(), nullable=False),
        sa.Column("sympy_expr", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. Variables table
    op.create_table(
        "variables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(36),
            sa.ForeignKey("research_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(30), nullable=False, server_default="real"),
        sa.Column("latex_presentation", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 3. Validation Runs table
    op.create_table(
        "validation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(36),
            sa.ForeignKey("research_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("overall_state", sa.String(30), nullable=False, server_default="NOT_YET_TESTED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 4. Validation Findings table
    op.create_table(
        "validation_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("validation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("layer", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_entity_type", sa.String(50), nullable=False, server_default="EQUATION"),
        sa.Column("target_entity_id", sa.String(64), nullable=False),
        sa.Column("job_id", sa.String(64), nullable=False, index=True),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("diagnostic_code", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("symbolic_simplification", sa.Text(), nullable=True),
        sa.Column("dimensions_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("diagnostics", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 5. Row-Level Security (RLS) DDL for Equations
    op.execute("ALTER TABLE equations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE equations FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_equations ON equations
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = equations.version_id
            AND (
                p.visibility = 'public_preprint'
                OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
                OR (
                    p.organization_id IS NOT NULL 
                    AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')
                )
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = equations.version_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)

    # 6. Row-Level Security (RLS) DDL for Variables
    op.execute("ALTER TABLE variables ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE variables FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_variables ON variables
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = variables.version_id
            AND (
                p.visibility = 'public_preprint'
                OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
                OR (
                    p.organization_id IS NOT NULL 
                    AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')
                )
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = variables.version_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)

    # 7. Row-Level Security (RLS) DDL for Validation Runs
    op.execute("ALTER TABLE validation_runs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE validation_runs FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_validation_runs ON validation_runs
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = validation_runs.version_id
            AND (
                p.visibility = 'public_preprint'
                OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
                OR (
                    p.organization_id IS NOT NULL 
                    AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')
                )
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = validation_runs.version_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)

    # 8. Row-Level Security (RLS) DDL for Validation Findings
    op.execute("ALTER TABLE validation_findings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE validation_findings FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_validation_findings ON validation_findings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM validation_runs r
            JOIN research_versions v ON v.id = r.version_id
            JOIN research_projects p ON p.id = v.project_id
            WHERE r.id = validation_findings.run_id
            AND (
                p.visibility = 'public_preprint'
                OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
                OR (
                    p.organization_id IS NOT NULL 
                    AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')
                )
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM validation_runs r
            JOIN research_versions v ON v.id = r.version_id
            JOIN research_projects p ON p.id = v.project_id
            WHERE r.id = validation_findings.run_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_validation_findings ON validation_findings;")
    op.drop_table("validation_findings")
    op.execute("DROP POLICY IF EXISTS rls_validation_runs ON validation_runs;")
    op.drop_table("validation_runs")
    op.execute("DROP POLICY IF EXISTS rls_variables ON variables;")
    op.drop_table("variables")
    op.execute("DROP POLICY IF EXISTS rls_equations ON equations;")
    op.drop_table("equations")

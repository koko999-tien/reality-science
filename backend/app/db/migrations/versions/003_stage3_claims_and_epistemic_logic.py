"""Stage 3 Claims and Epistemic Logic Schema: claims and claim_relations with Row-Level Security (RLS)

Revision ID: 003_stage3_claims_and_epistemic_logic
Revises: 002_stage1_validation_and_math
Create Date: 2026-11-15 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_stage3_claims_and_epistemic_logic"
down_revision: Union[str, None] = "002_stage1_validation_and_math"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preserve the existing revision ID, which exceeds Alembic's default 32 chars.
    # This also supports databases already at revision002; no history is renamed.
    op.alter_column("alembic_version", "version_num", type_=sa.String(64), existing_type=sa.String(32))
    # 1. Claims table
    op.create_table(
        "claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(36),
            sa.ForeignKey("research_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("claim_code", sa.String(50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(50), nullable=False, server_default="HYPOTHESIS"),
        sa.Column("target_variable", sa.String(50), nullable=True),
        sa.Column("canonical_ast_json", sa.JSON(), nullable=True),
        sa.Column("assumptions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("epistemic_state", sa.String(30), nullable=False, server_default="NOT_YET_TESTED"),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("dependency_logic", sa.String(10), nullable=False, server_default="ALL"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. Claim Relations table
    op.create_table(
        "claim_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(36),
            sa.ForeignKey("research_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_claim_id",
            sa.String(36),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_claim_id",
            sa.String(36),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relation_type", sa.String(50), nullable=False, server_default="DEPENDS_ON"),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 3. Row-Level Security (RLS) DDL for Claims
    op.execute("ALTER TABLE claims ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE claims FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_claims ON claims
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = claims.version_id
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
            WHERE v.id = claims.version_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)

    # 4. Row-Level Security (RLS) DDL for Claim Relations
    op.execute("ALTER TABLE claim_relations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE claim_relations FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY rls_claim_relations ON claim_relations
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM research_versions v
            JOIN research_projects p ON p.id = v.project_id
            WHERE v.id = claim_relations.version_id
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
            WHERE v.id = claim_relations.version_id
            AND p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')
        )
    );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_claim_relations ON claim_relations;")
    op.drop_table("claim_relations")
    op.execute("DROP POLICY IF EXISTS rls_claims ON claims;")
    op.drop_table("claims")

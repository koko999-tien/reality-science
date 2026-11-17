"""Draft concurrency tokens, unit definitions and mathematical-content freeze.

Revision ID: 005_atomic_drafts
Revises: 004_owner_only_dml
"""
from alembic import op
import sqlalchemy as sa

revision = "005_atomic_drafts"
down_revision = "004_owner_only_dml"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("research_versions", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("research_versions", sa.Column("units_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("validation_runs", sa.Column("input_revision", sa.Integer(), nullable=True))
    # NULL preserves deterministic legacy ordering; draft saves assign explicit order.
    op.add_column("equations", sa.Column("position", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_equation_position", "equations", "position IS NULL OR position >= 0")
    # Existing duplicate version numbers require data reconciliation, never silent renumbering.
    op.create_unique_constraint("uq_project_version_number", "research_versions", ["project_id", "version_number"])
    op.create_check_constraint("ck_version_revision", "research_versions", "revision >= 0")
    op.execute("""
    CREATE FUNCTION fn_version_units_revision() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.units_json::jsonb IS DISTINCT FROM OLD.units_json::jsonb THEN
            NEW.revision := GREATEST(NEW.revision, OLD.revision + 1);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_version_units_revision BEFORE UPDATE ON research_versions
    FOR EACH ROW EXECUTE FUNCTION fn_version_units_revision();
    """)
    op.execute("""
    CREATE FUNCTION fn_math_content_revision() RETURNS TRIGGER AS $$
    DECLARE parent_id varchar(36); frozen boolean;
    BEGIN
        IF TG_OP = 'UPDATE' AND NEW.version_id IS DISTINCT FROM OLD.version_id THEN
            RAISE EXCEPTION 'CANNOT_REPARENT_MATH_CONTENT';
        END IF;
        IF TG_OP = 'DELETE' THEN parent_id := OLD.version_id;
        ELSE parent_id := NEW.version_id; END IF;
        SELECT is_frozen INTO frozen FROM research_versions WHERE id = parent_id FOR UPDATE;
        IF frozen THEN
            RAISE EXCEPTION 'CANNOT_MODIFY_FROZEN_VERSION: %', parent_id;
        END IF;
        -- Serialize every mathematical write with draft save, including legacy CRUD.
        UPDATE research_versions SET revision = revision + 1 WHERE id = parent_id;
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END;
    $$ LANGUAGE plpgsql;
    """)
    for table in ("equations", "variables", "claims", "claim_relations"):
        op.execute(f"""CREATE TRIGGER trg_{table}_revision
            BEFORE INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION fn_math_content_revision()""")
    for table in ("draft_audit_events", "outbox_events"):
        columns = [sa.Column("id", sa.String(36), primary_key=True),
                   sa.Column("version_id", sa.String(36), sa.ForeignKey("research_versions.id"), nullable=False),
                   sa.Column("actor_id", sa.String(36), nullable=False),
                   sa.Column("action", sa.String(50), nullable=False),
                   sa.Column("payload", sa.JSON(), nullable=False),
                   sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)]
        if table == "draft_audit_events":
            columns += [sa.Column("sequence", sa.Integer(), nullable=False),
                        sa.Column("prev_hash", sa.String(64), nullable=False),
                        sa.Column("event_hash", sa.String(64), nullable=False)]
        op.create_table(table, *columns)
        op.create_index(f"ix_{table}_version", table, ["version_id"])
        if table == "draft_audit_events":
            op.create_unique_constraint("uq_draft_event_sequence", table, ["version_id", "sequence"])
            op.create_unique_constraint("uq_draft_event_successor", table, ["version_id", "prev_hash"])
            op.create_check_constraint("ck_draft_event_sequence", table, "sequence > 0")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        owner = f"""EXISTS (SELECT 1 FROM research_versions v JOIN research_projects p ON p.id=v.project_id
            WHERE v.id={table}.version_id AND p.owner_actor_id=NULLIF(current_setting('app.current_actor_id',true),''))"""
        op.execute(f"CREATE POLICY rls_{table}_select ON {table} FOR SELECT USING ({owner})")
        op.execute(f"CREATE POLICY rls_{table}_insert ON {table} FOR INSERT WITH CHECK ({owner})")
    op.execute("""
    CREATE FUNCTION fn_immutable_draft_event() RETURNS TRIGGER AS $$
    BEGIN RAISE EXCEPTION 'IMMUTABLE_DRAFT_EVENT'; END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_draft_audit_immutable BEFORE UPDATE OR DELETE ON draft_audit_events
    FOR EACH ROW EXECUTE FUNCTION fn_immutable_draft_event();
    """)


def downgrade():
    op.drop_table("draft_audit_events")
    op.drop_table("outbox_events")
    op.execute("DROP FUNCTION fn_immutable_draft_event()")
    op.execute("DROP TRIGGER trg_version_units_revision ON research_versions")
    op.execute("DROP FUNCTION fn_version_units_revision()")
    for table in ("equations", "variables", "claims", "claim_relations"):
        op.execute(f"DROP TRIGGER trg_{table}_revision ON {table}")
    op.execute("DROP FUNCTION fn_math_content_revision()")
    op.drop_constraint("ck_version_revision", "research_versions")
    op.drop_constraint("uq_project_version_number", "research_versions")
    op.drop_column("validation_runs", "input_revision")
    op.drop_constraint("ck_equation_position", "equations")
    op.drop_column("equations", "position")
    op.drop_column("research_versions", "units_json")
    op.drop_column("research_versions", "revision")

import sqlite3
import pytest


@pytest.fixture
def sqlite_db():
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON;")

    con.execute("""
    CREATE TABLE user_accounts (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        is_active INTEGER DEFAULT 1 NOT NULL
    );
    """)
    con.execute("""
    CREATE TABLE research_actors (
        id TEXT PRIMARY KEY,
        user_account_id TEXT REFERENCES user_accounts(id) ON DELETE SET NULL,
        display_name TEXT NOT NULL,
        is_anonymized INTEGER DEFAULT 0 NOT NULL
    );
    """)
    con.execute("""
    CREATE TABLE research_projects (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        owner_actor_id TEXT NOT NULL REFERENCES research_actors(id),
        organization_id TEXT NULL,
        visibility TEXT DEFAULT 'private_draft' NOT NULL CHECK (visibility IN ('private_draft', 'public_preprint')),
        is_frozen INTEGER DEFAULT 0 NOT NULL
    );
    """)
    con.execute("""
    CREATE TABLE research_versions (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
        version_number INTEGER DEFAULT 1 NOT NULL,
        title TEXT NOT NULL,
        is_frozen INTEGER DEFAULT 0 NOT NULL
    );
    """)

    # SQLite Freeze Triggers (emulating Postgres trg_freeze_research_versions)
    con.execute("""
    CREATE TRIGGER trg_freeze_research_versions_update
    BEFORE UPDATE ON research_versions
    FOR EACH ROW
    WHEN OLD.is_frozen = 1
    BEGIN
        SELECT RAISE(ABORT, 'CANNOT_MODIFY_FROZEN_VERSION: Research version is frozen.');
    END;
    """)
    con.execute("""
    CREATE TRIGGER trg_freeze_research_versions_delete
    BEFORE DELETE ON research_versions
    FOR EACH ROW
    WHEN OLD.is_frozen = 1
    BEGIN
        SELECT RAISE(ABORT, 'CANNOT_MODIFY_FROZEN_VERSION: Research version is frozen.');
    END;
    """)

    yield con
    con.close()


def test_right_to_erasure_preserves_scholarly_lineage(sqlite_db):
    """Verifies that deleting a UserAccount sets research_actors.user_account_id = NULL without deleting actor or project."""
    sqlite_db.execute("INSERT INTO user_accounts VALUES ('u_1', 'researcher@inst.edu', 1);")
    sqlite_db.execute("INSERT INTO research_actors VALUES ('act_1', 'u_1', 'Dr. Researcher', 0);")
    sqlite_db.execute("INSERT INTO research_projects VALUES ('proj_1', 'quantum-gravity-bounds', 'QG Bounds', 'act_1', NULL, 'private_draft', 0);")

    # Verify initial link
    actor = sqlite_db.execute("SELECT user_account_id, display_name FROM research_actors WHERE id = 'act_1'").fetchone()
    assert actor[0] == "u_1"

    # Execute right-to-erasure account deletion
    sqlite_db.execute("DELETE FROM user_accounts WHERE id = 'u_1';")

    # Assert user account is expunged
    assert sqlite_db.execute("SELECT * FROM user_accounts WHERE id = 'u_1'").fetchone() is None

    # Assert research actor persists with user_account_id = NULL
    anonymized_actor = sqlite_db.execute("SELECT user_account_id, display_name FROM research_actors WHERE id = 'act_1'").fetchone()
    assert anonymized_actor[0] is None
    assert anonymized_actor[1] == "Dr. Researcher"

    # Assert project remains intact and attributed
    project = sqlite_db.execute("SELECT owner_actor_id, title FROM research_projects WHERE id = 'proj_1'").fetchone()
    assert project[0] == "act_1"
    assert project[1] == "QG Bounds"


def test_project_visibility_check_constraint(sqlite_db):
    """Verifies that project visibility strictly rejects values outside 'private_draft' and 'public_preprint'."""
    sqlite_db.execute("INSERT INTO user_accounts VALUES ('u_2', 'user2@inst.edu', 1);")
    sqlite_db.execute("INSERT INTO research_actors VALUES ('act_2', 'u_2', 'Actor Two', 0);")

    # Allowed states
    sqlite_db.execute("INSERT INTO research_projects VALUES ('p_draft', 'slug-1', 'Draft', 'act_2', NULL, 'private_draft', 0);")
    sqlite_db.execute("INSERT INTO research_projects VALUES ('p_pub', 'slug-2', 'Preprint', 'act_2', NULL, 'public_preprint', 0);")

    # Disallowed state raises IntegrityError
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        sqlite_db.execute("INSERT INTO research_projects VALUES ('p_bad', 'slug-3', 'Bad', 'act_2', NULL, 'unauthorized_stage', 0);")


def test_research_version_freeze_trigger_blocks_mutation(sqlite_db):
    """Verifies that when is_frozen = 1, subsequent UPDATE and DELETE operations are rejected with CANNOT_MODIFY_FROZEN_VERSION."""
    sqlite_db.execute("INSERT INTO user_accounts VALUES ('u_3', 'user3@inst.edu', 1);")
    sqlite_db.execute("INSERT INTO research_actors VALUES ('act_3', 'u_3', 'Actor Three', 0);")
    sqlite_db.execute("INSERT INTO research_projects VALUES ('p_v', 'slug-v', 'Versions Project', 'act_3', NULL, 'private_draft', 0);")

    # 1. Unfrozen draft allows mutation
    sqlite_db.execute("INSERT INTO research_versions VALUES ('ver_1', 'p_v', 1, 'Draft Version Title', 0);")
    sqlite_db.execute("UPDATE research_versions SET title = 'Refined Draft Title' WHERE id = 'ver_1';")
    assert sqlite_db.execute("SELECT title FROM research_versions WHERE id = 'ver_1'").fetchone()[0] == "Refined Draft Title"

    # 2. Freeze version
    sqlite_db.execute("UPDATE research_versions SET is_frozen = 1 WHERE id = 'ver_1';")

    # 3. Mutation is strictly rejected
    with pytest.raises(sqlite3.IntegrityError, match="CANNOT_MODIFY_FROZEN_VERSION"):
        sqlite_db.execute("UPDATE research_versions SET title = 'Illegally Mutated Title' WHERE id = 'ver_1';")

    # 4. Deletion is strictly rejected
    with pytest.raises(sqlite3.IntegrityError, match="CANNOT_MODIFY_FROZEN_VERSION"):
        sqlite_db.execute("DELETE FROM research_versions WHERE id = 'ver_1';")


def test_unfrozen_draft_version_deletion_succeeds(sqlite_db):
    """Verifies that an unfrozen draft version (is_frozen = 0) can be deleted cleanly."""
    sqlite_db.execute("INSERT INTO user_accounts VALUES ('u_4', 'user4@inst.edu', 1);")
    sqlite_db.execute("INSERT INTO research_actors VALUES ('act_4', 'u_4', 'Actor Four', 0);")
    sqlite_db.execute("INSERT INTO research_projects VALUES ('p_draft_del', 'slug-del', 'Draft Del', 'act_4', NULL, 'private_draft', 0);")
    sqlite_db.execute("INSERT INTO research_versions VALUES ('ver_draft', 'p_draft_del', 1, 'Draft Version To Delete', 0);")

    # Deletion of unfrozen draft succeeds cleanly
    sqlite_db.execute("DELETE FROM research_versions WHERE id = 'ver_draft';")
    assert sqlite_db.execute("SELECT * FROM research_versions WHERE id = 'ver_draft'").fetchone() is None

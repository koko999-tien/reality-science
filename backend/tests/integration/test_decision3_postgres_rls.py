import os
import socket
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


def is_postgres_available() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="Live PostgreSQL daemon (port 5432) is not reachable in current environment",
)


@pytest.mark.asyncio
async def test_postgres_rls_isolation():
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://rs_app_user:app_secure_password@localhost:5432/reality_science",
    )
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        # Seed research actor A before inserting project to satisfy foreign key constraint
        await conn.execute(
            text(
                """
            INSERT INTO research_actors (id, display_name)
            VALUES ('actor-a-uuid', 'Actor A')
            ON CONFLICT (id) DO NOTHING;
            """
            )
        )
        # Actor A context
        await conn.execute(text("SET LOCAL app.current_actor_id = 'actor-a-uuid';"))
        await conn.execute(
            text(
                """
            INSERT INTO research_projects (id, slug, title, owner_actor_id, visibility)
            VALUES ('proj-a-1', 'private-a', 'Private Project A', 'actor-a-uuid', 'private_draft')
            ON CONFLICT (id) DO NOTHING;
        """
            )
        )

    async with engine.begin() as conn:
        # Actor B context attempting to read Actor A's private draft
        await conn.execute(text("SET LOCAL app.current_actor_id = 'actor-b-uuid';"))
        result = await conn.execute(
            text("SELECT id FROM research_projects WHERE id = 'proj-a-1';")
        )
        rows = result.fetchall()
        assert len(rows) == 0, "Security Violation: Actor B was able to read Actor A's private draft!"

    await engine.dispose()

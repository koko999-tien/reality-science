"""Additional NEW-owner regression; the original85 live cases stay unchanged."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.test_decision3_postgres_rls import context, pg, records


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility", ["private_draft", "public_preprint"])
async def test_owner_cannot_transfer_project_ownership(pg, records, visibility):
    row_id = records[visibility]["research_projects"]
    async with pg.connect() as conn:
        await context(conn, records["owner"], records["org"])
        with pytest.raises(DBAPIError) as exc:
            await conn.execute(text("UPDATE research_projects SET owner_actor_id=:outsider WHERE id=:id"),
                               {"outsider": records["outsider"], "id": row_id})
        assert exc.value.orig.sqlstate == "42501"
        await conn.rollback()
    async with pg.begin() as fresh:
        await context(fresh, records["owner"])
        assert (await fresh.execute(text("SELECT owner_actor_id FROM research_projects WHERE id=:id"),
                                    {"id": row_id})).scalar_one() == records["owner"]

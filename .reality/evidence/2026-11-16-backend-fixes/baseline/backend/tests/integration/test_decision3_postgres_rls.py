"""Real PostgreSQL RLS checks. Explicit disposable target required; no port probing."""

import asyncio
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.iam_governance.dependencies import _set_actor_context
from app.modules.iam_governance.models import ResearchActor
from tests.postgres_target import disposable_target, verify_disposable_connection


TABLES = ("research_projects", "research_versions", "equations", "variables", "claims",
          "claim_relations", "validation_runs", "validation_findings")


@pytest_asyncio.fixture
async def pg():
    target = disposable_target(os.environ)
    if target is None:
        pytest.skip("Explicit REALITY_TEST_DATABASE_URL and REALITY_TEST_INSTANCE_ID required")
    engine = create_async_engine(target.url, pool_size=1, max_overflow=0, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            await verify_disposable_connection(connection, target)
        yield engine
    finally:
        await engine.dispose()


async def context(connection, actor="", org=""):
    await connection.execute(text("SELECT set_config('app.current_actor_id', :actor, true), "
                                  "set_config('app.current_org_id', :org, true)"),
                             {"actor": actor, "org": org})


@pytest_asyncio.fixture
async def records(pg):
    """Commit test-owned rows, so a different session must actually read persisted data."""
    owner, outsider, org = (str(uuid.uuid4()) for _ in range(3))
    result = {"owner": owner, "outsider": outsider, "org": org}
    async with pg.begin() as conn:
        for actor in (owner, outsider):
            await conn.execute(text("INSERT INTO research_actors(id, display_name) VALUES (:id, :name)"),
                               {"id": actor, "name": "Disposable RLS fixture"})
        for key, actor, visibility in (("private_draft", owner, "private_draft"),
                                       ("public_preprint", owner, "public_preprint"),
                                       ("outsider_owned", outsider, "private_draft")):
            await context(conn, actor, org)
            ids = {table: str(uuid.uuid4()) for table in TABLES}
            result[key] = ids
            await conn.execute(text("""INSERT INTO research_projects
                (id, slug, title, owner_actor_id, organization_id, visibility)
                VALUES (:id, :id, 'Disposable RLS fixture', :owner, :org, :visibility)"""),
                {"id": ids["research_projects"], "owner": actor, "org": org, "visibility": visibility})
            await conn.execute(text("""INSERT INTO research_versions(id, project_id, title)
                VALUES (:id, :project, 'Disposable version')"""),
                {"id": ids["research_versions"], "project": ids["research_projects"]})
            for table, columns, values in (
                ("equations", "label, latex_raw, canonical_ast_json", "'x', 'x', '{\"node_type\":\"variable\",\"value\":\"x\"}'"),
                ("variables", "symbol, name, unit", "'x', 'position', 'm'"),
                ("claims", "claim_code, statement", "'FIXTURE', 'Test fixture only'"),
                ("validation_runs", "status", "'pending'"),
            ):
                await conn.execute(text(f"INSERT INTO {table}(id, version_id, {columns}) VALUES (:id, :version, {values})"),
                                   {"id": ids[table], "version": ids["research_versions"]})
            await conn.execute(text("""INSERT INTO claim_relations(id, version_id, source_claim_id, target_claim_id)
                VALUES (:id, :version, :claim, :claim)"""),
                {"id": ids["claim_relations"], "version": ids["research_versions"], "claim": ids["claims"]})
            await conn.execute(text("""INSERT INTO validation_findings
                (id, run_id, target_entity_id, job_id, state, diagnostic_code, message)
                VALUES (:id, :run, :equation, :job, 'NOT_YET_TESTED', 'FIXTURE', 'No scientific run')"""),
                {"id": ids["validation_findings"], "run": ids["validation_runs"],
                 "equation": ids["equations"], "job": str(uuid.uuid4())})
    return result


@pytest.mark.asyncio
async def test_all_project_tables_force_rls(pg):
    async with pg.connect() as conn:
        rows = (await conn.execute(text("""SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relname = ANY(:tables)"""),
            {"tables": list(TABLES)})).all()
        assert len(rows) == len(TABLES)
        assert all(enabled and forced for _, enabled, forced in rows)


@pytest.mark.asyncio
@pytest.mark.parametrize("table", TABLES)
async def test_owner_positive_outsider_negative_and_public_read(pg, records, table):
    private = records["private_draft"][table]
    public = records["public_preprint"][table]
    for actor, org, private_visible in (
        (records["owner"], "", True), (records["outsider"], "", False), ("", "", False),
        (records["outsider"], records["org"], True),
    ):
        async with pg.begin() as conn:
            await context(conn, actor, org)
            ids = (await conn.execute(text(f"SELECT id FROM {table} WHERE id IN (:private, :public)"),
                                     {"private": private, "public": public})).scalars().all()
            assert public in ids
            assert (private in ids) == private_visible


@pytest.mark.asyncio
@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("visibility", ["private_draft", "public_preprint"])
@pytest.mark.parametrize("reader", ["outsider", "org_peer", "anonymous"])
async def test_nonowner_cannot_delete_any_project_record(pg, records, table, visibility, reader):
    async with pg.connect() as conn:
        await context(conn, "" if reader == "anonymous" else records["outsider"],
                      records["org"] if reader == "org_peer" else "")
        result = await conn.execute(text(f"DELETE FROM {table} WHERE id = :id RETURNING id"),
                                    {"id": records[visibility][table]})
        deleted = result.scalars().all()
        await conn.rollback()
        assert deleted == []


@pytest.mark.asyncio
async def test_public_project_cannot_be_taken_over(pg, records):
    async with pg.connect() as conn:
        await context(conn, records["outsider"])
        result = await conn.execute(text("""UPDATE research_projects SET owner_actor_id = :actor
            WHERE id = :id RETURNING id"""),
            {"actor": records["outsider"], "id": records["public_preprint"]["research_projects"]})
        changed = result.scalars().all()
        await conn.rollback()
        assert changed == []


@pytest.mark.asyncio
@pytest.mark.parametrize("table", TABLES[1:])
async def test_nonowner_cannot_reparent_visible_records(pg, records, table):
    column, parent = (("project_id", "research_projects") if table == "research_versions" else
                      ("run_id", "validation_runs") if table == "validation_findings" else
                      ("version_id", "research_versions"))
    for visibility, org in (("public_preprint", ""), ("private_draft", records["org"])):
        async with pg.connect() as conn:
            await context(conn, records["outsider"], org)
            result = await conn.execute(text(f"UPDATE {table} SET {column}=:parent WHERE id=:id RETURNING id"),
                                        {"parent": records["outsider_owned"][parent], "id": records[visibility][table]})
            changed = result.scalars().all()
            await conn.rollback()
            assert changed == []


@pytest.mark.asyncio
async def test_nonowner_insert_rejected_and_owner_write_persists(pg, records):
    version = records["private_draft"]["research_versions"]
    query = text("INSERT INTO variables(id, version_id, symbol, name, unit) VALUES (:id, :version, 'y', 'y', 'm')")
    async with pg.connect() as conn:
        await context(conn, records["outsider"])
        with pytest.raises(DBAPIError) as exc:
            await conn.execute(query, {"id": str(uuid.uuid4()), "version": version})
        assert exc.value.orig.sqlstate == "42501"
        await conn.rollback()
    row_id = str(uuid.uuid4())
    async with pg.begin() as conn:
        await context(conn, records["owner"])
        await conn.execute(query, {"id": row_id, "version": version})
    async with pg.begin() as fresh:
        await context(fresh, records["owner"])
        assert (await fresh.execute(text("SELECT symbol FROM variables WHERE id = :id"), {"id": row_id})).scalar_one() == "y"


@pytest.mark.asyncio
@pytest.mark.parametrize("table", TABLES)
async def test_owner_crud_and_nonowner_insert_update_guards(pg, records, table):
    for visibility in ("private_draft", "public_preprint"):
        row_id = records[visibility][table]
        async with pg.begin() as conn:
            await context(conn, records["owner"])
            record = (await conn.execute(text(f"SELECT row_to_json(t) FROM {table} t WHERE id=:id"),
                                         {"id": row_id})).scalar_one()
        copy_id = str(uuid.uuid4())
        record["id"] = copy_id
        if table == "research_projects":
            record["slug"] = copy_id
        insert = text(f"INSERT INTO {table} SELECT (json_populate_record(NULL::{table}, CAST(:row AS json))).*")
        for actor, org in ((records["outsider"], ""), (records["outsider"], records["org"]), ("", "")):
            async with pg.connect() as conn:
                await context(conn, actor, org)
                with pytest.raises(DBAPIError) as exc:
                    await conn.execute(insert, {"row": json.dumps(record)})
                assert exc.value.orig.sqlstate == "42501"
                await conn.rollback()
                await context(conn, actor, org)
                updated = (await conn.execute(text(f"UPDATE {table} SET id=id WHERE id=:id RETURNING id"),
                                              {"id": row_id})).scalars().all()
                await conn.rollback()
                assert updated == []
        async with pg.begin() as conn:
            await context(conn, records["owner"])
            await conn.execute(insert, {"row": json.dumps(record)})
        async with pg.begin() as fresh:
            await context(fresh, records["owner"])
            assert (await fresh.execute(text(f"SELECT id FROM {table} WHERE id=:id"),
                                        {"id": copy_id})).scalar_one() == copy_id
        for operation in (f"UPDATE {table} SET id=id", f"DELETE FROM {table}"):
            async with pg.connect() as conn:
                await context(conn, records["owner"])
                assert (await conn.execute(text(f"{operation} WHERE id=:id RETURNING id"),
                                           {"id": copy_id})).scalar_one() == copy_id
                await conn.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("table", TABLES[1:])
async def test_owner_cannot_move_record_to_another_owners_parent(pg, records, table):
    column, parent = (("project_id", "research_projects") if table == "research_versions" else
                      ("run_id", "validation_runs") if table == "validation_findings" else
                      ("version_id", "research_versions"))
    async with pg.connect() as conn:
        await context(conn, records["owner"], records["org"])
        with pytest.raises(DBAPIError) as exc:
            await conn.execute(text(f"UPDATE {table} SET {column}=:parent WHERE id=:id"),
                               {"parent": records["outsider_owned"][parent], "id": records["private_draft"][table]})
        assert exc.value.orig.sqlstate == "42501"
        await conn.rollback()


@pytest.mark.asyncio
async def test_actor_context_commit_rollback_and_reused_connection(pg, records):
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    owner = ResearchActor(id=records["owner"], display_name="Fixture", organization_id=records["org"])
    outsider = ResearchActor(id=records["outsider"], display_name="Fixture", organization_id=None)
    query = text("SELECT current_setting('app.current_actor_id', true), "
                 "current_setting('app.current_org_id', true), pg_backend_pid()")
    async with sessions() as session:
        # Authentication starts a transaction before resolving actor context.
        await session.execute(text("SELECT 1"))
        await _set_actor_context(session, owner)
        first = (await session.execute(query)).one()
        for finish in (session.commit, session.rollback, session.commit):
            await finish()
            assert (await session.execute(query)).one() == first
        assert first[:2] == (owner.id, owner.organization_id)
    async with sessions() as anonymous:
        blank = (await anonymous.execute(query)).one()
        assert blank[2] == first[2]  # pool_size=1: same physical connection, new request
        assert not blank[0] and not blank[1]
        assert (await anonymous.execute(text("SELECT id FROM research_projects WHERE id = :id"),
                                       {"id": records["private_draft"]["research_projects"]})).first() is None
    async with sessions() as session:
        await _set_actor_context(session, outsider)
        current = (await session.execute(query)).one()
        assert current == (outsider.id, "", first[2])
        await session.rollback()
        assert (await session.execute(query)).one() == current


@pytest.mark.asyncio
async def test_failed_transaction_rolls_back_rows_and_actor_context(pg, records):
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    actor = ResearchActor(id=records["owner"], display_name="Fixture", organization_id=records["org"])
    row_id = str(uuid.uuid4())
    insert = text("INSERT INTO variables(id,version_id,symbol,name,unit) VALUES (:id,:version,'z','z','m')")
    async with sessions() as session:
        await _set_actor_context(session, actor)
        pid = (await session.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        params = {"id": row_id, "version": records["private_draft"]["research_versions"]}
        await session.execute(insert, params)
        with pytest.raises(DBAPIError) as exc:
            await session.execute(insert, params)  # actual unique violation aborts the transaction
        assert exc.value.orig.sqlstate == "23505"
        await session.rollback()
        assert (await session.execute(text("SELECT current_setting('app.current_actor_id')"))).scalar_one() == actor.id
        assert (await session.execute(text("SELECT id FROM variables WHERE id=:id"), {"id": row_id})).first() is None
    async with sessions() as fresh:
        state = (await fresh.execute(text("SELECT pg_backend_pid(), current_setting('app.current_actor_id',true), "
                                          "current_setting('app.current_org_id',true)"))).one()
        assert state[0] == pid and not state[1] and not state[2]


@pytest_asyncio.fixture
async def live_api(pg, tmp_path):
    """Actual Uvicorn HTTP server + actual app pool, JWT, password hashing and DB.

    No dependency overrides or compute mocks. Current in-process worker import
    rejects the API's DB environment; successful queued compute is not covered.
    """
    target = disposable_target(os.environ)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    backend = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.update(DATABASE_URL=target.url.render_as_string(hide_password=False),
               JWT_SECRET_KEY=secrets.token_urlsafe(48), ENVIRONMENT="test",
               PYTHONPATH=os.pathsep.join(str(backend.parent / name) for name in ("backend", "shared", "worker")))
    # Log only server lifecycle; access logs could reveal fixture identifiers.
    with (tmp_path / "api.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(port), "--no-access-log"], cwd=backend, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
                deadline = time.monotonic() + 20
                while True:
                    if process.poll() is not None:
                        pytest.fail("Disposable API exited during startup; inspect fixture api.log")
                    try:
                        if (await client.get("/openapi.json")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if time.monotonic() > deadline:
                        pytest.fail("Disposable API startup timeout")
                    await asyncio.sleep(0.1)
                yield client
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # The Windows venv launcher can own the actual Python child.
                    # Stop this Popen-owned tree while its parent handle is live.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   check=True, capture_output=True)
                else:
                    process.terminate()
            process.wait(timeout=15)
            deadline = time.monotonic() + 3
            while True:
                with socket.socket() as sock:
                    sock.settimeout(0.2)
                    if sock.connect_ex(("127.0.0.1", port)) != 0:
                        break
                assert time.monotonic() < deadline, "Disposable API listener survived teardown"
                await asyncio.sleep(0.05)


async def register_login(client):
    email = f"fixture-{uuid.uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24)
    created = await client.post("/api/v1/iam/register", json={
        "email": email, "password": password, "display_name": "Disposable test actor"})
    assert created.status_code == 201
    invalid = await client.post("/api/v1/iam/login", json={"email": email, "password": "deliberately-invalid"})
    assert invalid.status_code == 401
    logged_in = await client.post("/api/v1/iam/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}, created.json()["id"]


@pytest.mark.asyncio
async def test_live_login_project_create_and_read_after_commit(live_api, pg):
    owner_headers, user_id = await register_login(live_api)
    outsider_headers, _ = await register_login(live_api)
    slug = f"live-{uuid.uuid4().hex}"
    payload = {"slug": slug, "title": "Disposable live project"}
    assert (await live_api.post("/api/v1/projects", json=payload)).status_code == 401
    created = await live_api.post("/api/v1/projects", headers=owner_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["versions"] == []  # no version-creation contract is invented
    route = f"/api/v1/projects/{slug}"
    for headers in ({}, {"X-Actor-Id": created.json()["owner_actor_id"]}, outsider_headers):
        assert (await live_api.get(route, headers=headers)).status_code == 404
    assert (await live_api.get(route, headers={"Authorization": "Bearer invalid"})).status_code == 401
    loaded = await live_api.get(route, headers=owner_headers)
    assert loaded.status_code == 200
    assert loaded.json()["id"] == created.json()["id"]
    async with pg.begin() as conn:
        actor_id = (await conn.execute(text("SELECT id FROM research_actors WHERE user_account_id=:id"),
                                      {"id": user_id})).scalar_one()
        await context(conn, actor_id)
        assert (await conn.execute(text("SELECT id FROM research_projects WHERE slug=:slug"),
                                   {"slug": slug})).scalar_one() == created.json()["id"]


@pytest.mark.asyncio
async def test_live_version_writes_history_and_access(live_api, pg):
    headers, user_id = await register_login(live_api)
    other_headers, _ = await register_login(live_api)
    version, public_version, private_project, public_project = (str(uuid.uuid4()) for _ in range(4))
    # Version creation is missing in the API. Seed only these fixture rows directly,
    # as the unprivileged owner, and identify this boundary in the evidence.
    async with pg.begin() as conn:
        actor = (await conn.execute(text("SELECT id FROM research_actors WHERE user_account_id=:id"),
                                   {"id": user_id})).scalar_one()
        await context(conn, actor)
        for project_id, version_id, visibility in ((private_project, version, "private_draft"),
                                                 (public_project, public_version, "public_preprint")):
            await conn.execute(text("""INSERT INTO research_projects(id,slug,title,owner_actor_id,visibility)
                VALUES (:id,:id,'Disposable API fixture',:actor,:visibility)"""),
                {"id": project_id, "actor": actor, "visibility": visibility})
            await conn.execute(text("INSERT INTO research_versions(id,project_id,title) VALUES (:id,:project,'Fixture')"),
                               {"id": version_id, "project": project_id})
    equation = {"label": "Force", "latex_raw": "m*a", "canonical_ast_json": {
        "node_type": "binary_op", "op": "*", "left": {"node_type": "variable", "value": "m"},
        "right": {"node_type": "variable", "value": "a"}}}
    for endpoint, payload in (
        ("equations", equation),
        ("variables", {"symbol": "m", "name": "mass", "unit": "kg"}),
        ("variables", {"symbol": "a", "name": "acceleration", "unit": "m/s^2"}),
    ):
        route = f"/api/v1/versions/{version}/{endpoint}"
        assert (await live_api.post(route, headers=other_headers, json=payload)).status_code == 404
        assert (await live_api.post(route, json=payload)).status_code == 401
        response = await live_api.post(route, headers=headers, json=payload)
        assert response.status_code == 201, response.text
        response_id = response.json()["id"]
        loaded = await live_api.get(route, headers=headers)
        assert loaded.status_code == 200
        assert response_id in {item["id"] for item in loaded.json()}
    for endpoint in ("equations", "variables", "claims", "claims/graph", "validation-runs"):
        route = f"/api/v1/versions/{version}/{endpoint}"
        assert (await live_api.get(route, headers=other_headers)).status_code == 404
        assert (await live_api.get(route)).status_code == 404
        assert (await live_api.get(f"/api/v1/versions/{public_version}/{endpoint}")).status_code == 200
    validate = f"/api/v1/versions/{version}/validate"
    assert (await live_api.post(validate)).status_code == 401
    assert (await live_api.post(validate, headers=other_headers)).status_code == 404
    result = await live_api.post(validate, headers=headers)
    assert result.status_code == 200, result.text
    run = result.json()
    assert run["overall_state"] == "PASS"
    assert run["version_id"] == version and len(run["findings"]) == 6
    history = await live_api.get(f"/api/v1/versions/{version}/validation-runs", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["id"] == run["id"]
    assert history.json()[0]["findings"] == run["findings"]
    async with pg.begin() as fresh:
        await context(fresh, actor)
        assert (await fresh.execute(text("SELECT overall_state FROM validation_runs WHERE id=:id"),
                                    {"id": run["id"]})).scalar_one() == "PASS"
        assert (await fresh.execute(text("SELECT count(*) FROM validation_findings WHERE run_id=:id"),
                                    {"id": run["id"]})).scalar_one() == 6
        # Master Brief: validation must not silently publish or change publication status.
        assert (await fresh.execute(text("SELECT publication_status FROM research_versions WHERE id=:id"),
                                    {"id": version})).scalar_one() == "draft"
    export = f"/api/v1/versions/{version}/export-zip"
    assert (await live_api.post(export)).status_code == 404
    assert (await live_api.post(export, headers=other_headers)).status_code == 404
    assert (await live_api.post(export, headers=headers)).status_code == 400

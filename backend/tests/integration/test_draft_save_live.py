"""Actual HTTP, unprivileged PostgreSQL, separate compute. No persistence mocks."""
import asyncio
import copy
import json
import os
from pathlib import Path
import uuid

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.test_decision3_postgres_rls import pg, live_api, register_login, context
from tests.integration.test_compute_queue_live import assert_queue_identity


def content(revision=0, unit="meter", value="x"):
    return {"expected_revision": revision,
            "equations": [{"label": "Position", "latex_raw": value,
                           "canonical_ast_json": {"node_type": "variable", "value": value}}],
            "variables": [{"symbol": value, "name": "Position", "unit": unit, "domain": "real"}],
            "units": []}


@pytest_asyncio.fixture
async def draft(live_api, pg):
    headers, user = await register_login(live_api)
    slug = "draft-" + uuid.uuid4().hex
    project = await live_api.post("/api/v1/projects", headers=headers, json={"slug": slug, "title": "Draft test"})
    assert project.status_code == 201, project.text
    version = await live_api.post(f"/api/v1/projects/{slug}/versions", headers=headers, json={"title": "First draft"})
    assert version.status_code == 201, version.text
    return {"headers": headers, "actor": project.json()["owner_actor_id"], "project": project.json(),
            "version": version.json(), "slug": slug, "route": f"/api/v1/versions/{version.json()['id']}"}


async def saved(client, fixture, payload):
    response = await client.put(fixture["route"] + "/draft", headers=fixture["headers"], json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def loaded(client, fixture):
    response = await client.get(fixture["route"] + "/draft", headers=fixture["headers"])
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_edit_save_reload_new_connection(live_api, pg, draft, tmp_path):
    payload = content(unit="draft_length")
    payload["units"] = [{"name": "draft_length", "symbol": "dlen", "dimensionality": "[length]", "scale_factor": 2.5}]
    result = await saved(live_api, draft, payload)
    assert result["version"]["revision"] > 0
    assert result["version"]["publication_status"] == "draft"
    assert result["version"]["content_hash"] is None and not result["version"]["is_frozen"]
    assert await loaded(live_api, draft) == result
    async with pg.begin() as connection:
        before_pid = (await connection.execute(text("SELECT pg_backend_pid()"))).scalar_one()
    await pg.dispose()  # force a genuinely new physical PostgreSQL connection
    async with pg.begin() as fresh:
        await context(fresh, draft["actor"])
        after_pid = (await fresh.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        assert after_pid != before_pid
        row = (await fresh.execute(text("SELECT revision,units_json FROM research_versions WHERE id=:id"), {"id": draft["version"]["id"]})).one()
        assert row[0] == result["version"]["revision"] and row[1] == payload["units"]
        ast = (await fresh.execute(text("SELECT canonical_ast_json FROM equations WHERE version_id=:id"), {"id": draft["version"]["id"]})).scalar_one()
        assert ast == payload["equations"][0]["canonical_ast_json"]
        assert (await fresh.execute(text("SELECT unit FROM variables WHERE version_id=:id"), {"id": draft["version"]["id"]})).scalar_one() == "draft_length"
        for table in ("draft_audit_events", "outbox_events"):
            assert (await fresh.execute(text(f"SELECT count(*) FROM {table} WHERE version_id=:id"), {"id": draft["version"]["id"]})).scalar_one() == 2
    (tmp_path / "read-after-write.json").write_text(json.dumps({"snapshot": result, "pid_before": before_pid, "pid_after": after_pid}, indent=2))


@pytest.mark.asyncio
async def test_concurrent_create_and_stale_save(live_api, pg, draft, tmp_path):
    route = f"/api/v1/projects/{draft['slug']}/versions"
    creates = await asyncio.gather(*(live_api.post(route, headers=draft["headers"], json={"title": title}) for title in ("Second", "Third")))
    assert all(r.status_code == 201 for r in creates)
    assert {r.json()["version_number"] for r in creates} == {2, 3}
    writes = [content(value="winner_a"), content(value="winner_b")]
    responses = await asyncio.gather(*(live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=p) for p in writes))
    assert sorted(r.status_code for r in responses) == [200, 409]
    winner = next(r.json() for r in responses if r.status_code == 200)
    conflict = next(r.json() for r in responses if r.status_code == 409)
    assert conflict["detail"]["code"] == "DRAFT_REVISION_CONFLICT"
    assert await loaded(live_api, draft) == winner
    assert winner["equations"][0]["canonical_ast_json"]["value"] == winner["variables"][0]["symbol"]
    (tmp_path / "conflict.json").write_text(json.dumps({"statuses": [r.status_code for r in responses], "winner": winner, "conflict": conflict}, indent=2))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["boolean", "undeclared", "duplicate", "depth", "power", "operator", "scale", "cross-version"])
async def test_invalid_draft_is_atomic(live_api, draft, kind):
    initial = await saved(live_api, draft, content())
    payload = content(initial["version"]["revision"])
    ast = payload["equations"][0]["canonical_ast_json"]
    if kind == "boolean": ast.update(node_type="constant", value=True)
    if kind == "undeclared": payload["variables"] = []
    if kind == "duplicate": payload["variables"] *= 2
    if kind == "depth":
        for _ in range(16): ast = {"node_type": "unary_op", "op": "neg", "left": ast}
        payload["equations"][0]["canonical_ast_json"] = ast
    if kind == "power": payload["equations"][0]["canonical_ast_json"] = {"node_type": "binary_op", "op": "**", "left": ast, "right": {"node_type": "constant", "value": 21}}
    if kind == "operator": payload["equations"][0]["canonical_ast_json"] = {"node_type": "unary_op", "op": "+", "left": ast}
    if kind == "scale": payload["units"] = [{"name": "bad", "symbol": "bad", "dimensionality": "[length]", "scale_factor": -1}]
    if kind == "cross-version": payload["equations"][0]["id"] = str(uuid.uuid4())
    response = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=payload)
    assert response.status_code == 422, response.text
    assert await loaded(live_api, draft) == initial


@pytest.mark.asyncio
async def test_owner_privacy_public_read_and_frozen_guards(live_api, pg, draft):
    other, _ = await register_login(live_api)
    for headers, expected in (({}, 401), (other, 404)):
        assert (await live_api.post(f"/api/v1/projects/{draft['slug']}/versions", headers=headers, json={"title": "Denied"})).status_code == expected
        assert (await live_api.put(draft["route"] + "/draft", headers=headers, json=content())).status_code == expected
        assert (await live_api.get(draft["route"] + "/draft", headers=headers)).status_code == 404
    initial = await saved(live_api, draft, content())
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        await conn.execute(text("UPDATE research_projects SET visibility='public_preprint' WHERE id=:id"), {"id": draft["project"]["id"]})
        await conn.execute(text("UPDATE research_versions SET is_frozen=true WHERE id=:id"), {"id": draft["version"]["id"]})
    for headers in ({}, other):
        assert (await live_api.get(draft["route"] + "/draft", headers=headers)).status_code == 200
    assert (await live_api.post(f"/api/v1/projects/{draft['slug']}/versions", headers=draft["headers"], json={"title": "Deferred public draft"})).status_code == 409
    response = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=content(initial["version"]["revision"]))
    assert response.status_code == 409 and "FROZEN" in response.text
    for table in ("equations", "variables"):
        async with pg.connect() as conn:
            await context(conn, draft["actor"])
            with pytest.raises(DBAPIError, match="CANNOT_MODIFY_FROZEN_VERSION"):
                await conn.execute(text(f"DELETE FROM {table} WHERE version_id=:id"), {"id": draft["version"]["id"]})
            await conn.rollback()


@pytest.mark.asyncio
async def test_database_failure_after_partial_writes_rolls_back(live_api, pg, draft, tmp_path):
    initial = await saved(live_api, draft, content())
    # An actual task-owned DB constraint fails on the replacement variable after
    # version/equation/old-variable writes have occurred. No API/ORM mock is used.
    from scripts.disposable_postgres import admin_connection
    manifest = json.loads(Path(os.environ["REALITY_DRAFT_MANIFEST"]).read_text())
    admin, _ = await admin_connection(manifest)
    constraint = "draft_fault_" + uuid.uuid4().hex
    try:
        await admin.execute(f"ALTER TABLE variables ADD CONSTRAINT {constraint} CHECK (name <> 'DRAFT_ROLLBACK_SENTINEL') NOT VALID")
        payload = content(initial["version"]["revision"], value="changed")
        payload["variables"][0]["name"] = "DRAFT_ROLLBACK_SENTINEL"
        payload["units"] = [{"name": "rollback_unit", "symbol": "rbu", "dimensionality": "[time]"}]
        response = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=payload)
        assert response.status_code == 500
        assert await loaded(live_api, draft) == initial
        await pg.dispose()
        async with pg.begin() as conn:
            await context(conn, draft["actor"])
            for table in ("outbox_events", "draft_audit_events"):
                assert (await conn.execute(text(f"SELECT count(*) FROM {table} WHERE version_id=:id"), {"id": draft["version"]["id"]})).scalar_one() == 2
        (tmp_path / "rollback.json").write_text(json.dumps({"http_status": 500, "snapshot_preserved": True, "events_preserved": True}, indent=2))
    finally:
        await admin.execute(f"ALTER TABLE variables DROP CONSTRAINT {constraint}")
        await admin.close()


@pytest.mark.asyncio
async def test_real_findings_stale_after_unit_edit_and_late_completion(live_api, pg, draft, tmp_path):
    await assert_queue_identity()
    payload = content(unit="version_unit")
    payload["equations"][0]["canonical_ast_json"] = {"node_type": "binary_op", "op": "+", "left": {"node_type": "variable", "value": "x"}, "right": {"node_type": "variable", "value": "y"}}
    payload["variables"].append({"symbol": "y", "name": "Reference length", "unit": "meter"})
    payload["units"] = [{"name": "version_unit", "symbol": "vunit", "dimensionality": "[length]", "scale_factor": 1}]
    first = await saved(live_api, draft, payload)
    check = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
    assert check.status_code == 200, check.text
    run = check.json()
    assert run["is_current"] and run["overall_state"] == "PASS"
    broker = Redis.from_url(os.environ["REDIS_URL"])
    key = "draft-test-hold:" + draft["version"]["id"]
    await broker.set(key, "1", ex=30)
    pending = asyncio.create_task(live_api.post(draft["route"] + "/validate", headers=draft["headers"]))
    try:
        for _ in range(100):
            if await broker.get(key + ":started"): break
            await asyncio.sleep(.05)
        assert await broker.get(key + ":started"), "Real worker did not reach pause checkpoint"
        payload["expected_revision"] = first["version"]["revision"]
        payload["equations"][0]["id"] = first["equations"][0]["id"]
        payload["units"][0]["dimensionality"] = "[time]"
        changed = await saved(live_api, draft, payload)
        await broker.rpush(key + ":release", "go")
        late = await pending
        assert late.status_code == 200, late.text
        assert late.json()["input_revision"] == first["version"]["revision"] and not late.json()["is_current"]
        history = (await live_api.get(draft["route"] + "/validation-runs", headers=draft["headers"])).json()
        assert len(history) == 2 and all(not r["is_current"] for r in history)
        await broker.delete(key)
        fresh = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
        assert fresh.status_code == 200, fresh.text
        current = fresh.json()
        assert current["is_current"] and current["input_revision"] == changed["version"]["revision"]
        assert current["overall_state"] == "FAIL"
        assert next(f for f in current["findings"] if f["layer"] == 3)["state"] == "FAIL"
        (tmp_path / "staleness.json").write_text(json.dumps({"first": run, "late": late.json(), "after_unit_edit": current}, indent=2))
    finally:
        await broker.rpush(key + ":release", "cleanup")
        await asyncio.gather(pending, return_exceptions=True)
        await broker.delete(key, key + ":started", key + ":release")
        await broker.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol,custom", [("v", False), ("u", False), ("v", True), ("u", True)])
async def test_declared_length_survives_real_worker_validation(live_api, pg, draft, symbol, custom):
    await assert_queue_identity()
    payload = content(unit="draft_length" if custom else "meter", value=symbol)
    payload["equations"][0]["canonical_ast_json"] = {
        "node_type": "binary_op", "op": "*", "left": {"node_type": "constant", "value": 2},
        "right": {"node_type": "variable", "value": symbol},
    }
    if custom:
        payload["units"] = [{"name": "draft_length", "symbol": "dlen", "dimensionality": "[length]", "scale_factor": 1000}]
    snapshot = await saved(live_api, draft, payload)
    checked = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
    assert checked.status_code == 200, checked.text
    run = checked.json()
    assert run["overall_state"] == "PASS" and run["is_current"]
    assert run["input_revision"] == snapshot["version"]["revision"]
    assert len(run["findings"]) == 6
    assert next(f for f in run["findings"] if f["layer"] == 4)["state"] == "PASS"
    await pg.dispose()
    history = (await live_api.get(draft["route"] + "/validation-runs", headers=draft["headers"])).json()
    assert len(history) == 1 and history[0]["id"] == run["id"]
    assert await loaded(live_api, draft) == snapshot


@pytest.mark.asyncio
async def test_custom_unit_alias_injection_cannot_persist_false_pass(live_api, pg, draft):
    await assert_queue_identity()
    payload = content()
    payload["variables"].append({"symbol": "t", "name": "Time", "unit": "second"})
    payload["equations"][0]["canonical_ast_json"] = {
        "node_type": "binary_op", "op": "+", "left": {"node_type": "variable", "value": "x"},
        "right": {"node_type": "variable", "value": "t"},
    }
    payload["units"] = [{"name": "draft_length", "symbol": "dlen = second = s", "dimensionality": "[length]"}]
    snapshot = await saved(live_api, draft, payload)
    checked = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
    assert checked.status_code == 200, checked.text
    run = checked.json()
    assert run["overall_state"] == "FAIL" and run["is_current"]
    assert next(f for f in run["findings"] if f["layer"] == 3)["diagnostic_code"] == "DIMENSIONAL_MISMATCH"
    await pg.dispose()
    async with pg.begin() as fresh:
        await context(fresh, draft["actor"])
        assert (await fresh.execute(text("SELECT overall_state FROM validation_runs WHERE id=:id"), {"id": run["id"]})).scalar_one() == "FAIL"
    assert await loaded(live_api, draft) == snapshot

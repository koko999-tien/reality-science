"""Additional real transactional boundaries for draft persistence."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.test_decision3_postgres_rls import pg, live_api, context
from tests.integration.test_draft_save_live import draft, content, loaded, saved


def from_snapshot(snapshot):
    return {"expected_revision": snapshot["version"]["revision"],
            "equations": [{k: e[k] for k in ("id", "label", "latex_raw", "canonical_ast_json")} for e in snapshot["equations"]],
            "variables": [{k: v[k] for k in ("symbol", "name", "unit", "domain", "latex_presentation")} for v in snapshot["variables"]],
            "units": snapshot["units"]}


@pytest.mark.asyncio
async def test_rich_snapshot_and_legacy_writes(live_api, pg, draft):
    payload = content()
    payload["equations"].append({"label": "Secondary", "latex_raw": "9", "canonical_ast_json": {"node_type": "constant", "value": 9}})
    first = await saved(live_api, draft, payload)
    edit = from_snapshot(first)
    edit["equations"][0]["latex_raw"] = "2*x"
    edit["equations"][0]["canonical_ast_json"] = {"node_type": "binary_op", "op": "*", "left": {"node_type": "constant", "value": 2}, "right": {"node_type": "variable", "value": "x"}}
    second = await saved(live_api, draft, edit)
    assert second["equations"][1] == first["equations"][1]
    legacy = await live_api.post(draft["route"] + "/variables", headers=draft["headers"], json={"symbol": "y", "name": "Legacy", "unit": "meter"})
    assert legacy.status_code == 201, legacy.text
    third = await loaded(live_api, draft)
    assert third["version"]["revision"] > second["version"]["revision"]
    conflict = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=from_snapshot(second))
    assert conflict.status_code == 409
    assert await loaded(live_api, draft) == third


@pytest.mark.asyncio
async def test_read_during_uncommitted_replace_is_coherent(live_api, pg, draft):
    first = await saved(live_api, draft, content())
    async with pg.connect() as conn:
        async with conn.begin():
            await context(conn, draft["actor"])
            await conn.execute(text("SELECT id FROM research_versions WHERE id=:id FOR UPDATE"), {"id": draft["version"]["id"]})
            await conn.execute(text("UPDATE equations SET latex_raw='x+x' WHERE version_id=:id"), {"id": draft["version"]["id"]})
            # A normal GET must not observe the partial transaction or block.
            assert await asyncio.wait_for(loaded(live_api, draft), 5) == first
            await conn.execute(text("UPDATE variables SET name='Committed name' WHERE version_id=:id"), {"id": draft["version"]["id"]})
        result = await loaded(live_api, draft)
    assert result["version"]["revision"] > first["version"]["revision"]
    assert result["equations"][0]["latex_raw"] == "x+x" and result["variables"][0]["name"] == "Committed name"


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["research_versions", "research_projects"])
async def test_freeze_wins_race_without_partial_save(live_api, pg, draft, scope):
    initial = await saved(live_api, draft, content())
    target = draft["version"]["id"] if scope == "research_versions" else draft["project"]["id"]
    async with pg.connect() as conn:
        transaction = await conn.begin()
        await context(conn, draft["actor"])
        await conn.execute(text(f"UPDATE {scope} SET is_frozen=true WHERE id=:id"), {"id": target})
        pending = asyncio.create_task(live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=content(initial["version"]["revision"], value="late")))
        await asyncio.sleep(.2)
        assert not pending.done(), "Save must wait for the freeze transaction"
        await transaction.commit()
        response = await pending
    assert response.status_code == 409, response.text
    final = await loaded(live_api, draft)
    assert final["equations"] == initial["equations"] and final["variables"] == initial["variables"]
    assert final["units"] == initial["units"] and final["version"]["revision"] == initial["version"]["revision"]


@pytest.mark.asyncio
async def test_events_chain_and_outbox_failure_roll_back(live_api, pg, draft):
    initial = await saved(live_api, draft, content())
    from scripts.disposable_postgres import admin_connection
    manifest = json.loads(Path(os.environ["REALITY_DRAFT_MANIFEST"]).read_text())
    admin, _ = await admin_connection(manifest)
    try:
        # Fails after all content and the audit insert, at the outbox insert.
        await admin.execute("ALTER TABLE outbox_events ADD CONSTRAINT draft_outbox_fault CHECK (action <> 'ResearchDraftSaved') NOT VALID")
        result = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=content(initial["version"]["revision"], value="rollback"))
        assert result.status_code == 500
        assert await loaded(live_api, draft) == initial
    finally:
        await admin.execute("ALTER TABLE outbox_events DROP CONSTRAINT draft_outbox_fault")
        await admin.close()
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        events = (await conn.execute(text("SELECT * FROM draft_audit_events WHERE version_id=:id ORDER BY sequence"), {"id": draft["version"]["id"]})).mappings().all()
        assert len(events) == 2
        previous = ""
        for event in events:
            canonical = json.dumps(event["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256((previous + event["actor_id"] + event["action"] + event["version_id"] + canonical + event["created_at"].isoformat()).encode()).hexdigest()
            assert event["prev_hash"] == previous and event["event_hash"] == digest
            previous = digest
        assert (await conn.execute(text("SELECT count(*) FROM outbox_events WHERE version_id=:id"), {"id": draft["version"]["id"]})).scalar_one() == 2
        for table in ("draft_audit_events", "outbox_events"):
            assert (await conn.execute(text(f"DELETE FROM {table} WHERE version_id=:id RETURNING id"), {"id": draft["version"]["id"]})).all() == []


@pytest.mark.asyncio
async def test_declaration_and_claim_input_changes_stale_history(live_api, pg, draft):
    first = await saved(live_api, draft, content())
    validated = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
    assert validated.status_code == 200 and validated.json()["is_current"]
    edit = from_snapshot(first)
    edit["variables"][0]["domain"] = "positive_real"
    second = await saved(live_api, draft, edit)
    history = (await live_api.get(draft["route"] + "/validation-runs", headers=draft["headers"])).json()
    assert all(not run["is_current"] for run in history)
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        await conn.execute(text("INSERT INTO claims (id,version_id,claim_code,statement,claim_type) VALUES (:id,:id,'C1','Claim input','HYPOTHESIS')"), {"id": draft["version"]["id"]})
        rev = (await conn.execute(text("SELECT revision FROM research_versions WHERE id=:id"), {"id": draft["version"]["id"]})).scalar_one()
        assert rev > second["version"]["revision"]
        await conn.execute(text("UPDATE claims SET epistemic_state='PASS' WHERE version_id=:id"), {"id": draft["version"]["id"]})
        assert (await conn.execute(text("SELECT revision FROM research_versions WHERE id=:id"), {"id": draft["version"]["id"]})).scalar_one() > rev


@pytest.mark.asyncio
async def test_existing_public_draft_save_and_sealed_rejection(live_api, pg, draft):
    initial = await saved(live_api, draft, content())
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        await conn.execute(text("UPDATE research_projects SET visibility='public_preprint' WHERE id=:id"), {"id": draft["project"]["id"]})
    second = await saved(live_api, draft, content(initial["version"]["revision"], value="public_x"))
    public = await live_api.get(draft["route"] + "/draft")
    assert public.status_code == 200 and public.json() == second
    assert (await live_api.put(draft["route"] + "/draft", json=from_snapshot(second))).status_code == 401
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        await conn.execute(text("UPDATE research_versions SET content_hash=:hash WHERE id=:id"), {"id": draft["version"]["id"], "hash": "f" * 64})
    rejected = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=from_snapshot(second))
    assert rejected.status_code == 409


@pytest.mark.asyncio
async def test_audit_clock_regression_and_insert_failure(live_api, pg, draft, monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.modules.research_core import events
    from scripts.disposable_postgres import admin_connection
    # Actual event inserts with equal/decreasing wall clocks under the same lock.
    async with async_sessionmaker(pg)() as session:
        session.info["research_actor_context"] = (draft["actor"], "")
        await context(session, draft["actor"])
        await session.execute(text("SELECT id FROM research_versions WHERE id=:id FOR UPDATE"), {"id": draft["version"]["id"]})
        for second in (3, 2, 2, 1):
            monkeypatch.setattr(events, "datetime", SimpleNamespace(now=lambda tz, s=second: datetime(2000, 1, 1, 0, 0, s, tzinfo=timezone.utc)))
            await events.record_draft_event(session, draft["version"]["id"], "ClockFixture", None, {"second": second})
        await session.commit()
    async with pg.begin() as conn:
        await context(conn, draft["actor"])
        rows = (await conn.execute(text("SELECT * FROM draft_audit_events WHERE version_id=:id ORDER BY sequence"), {"id": draft["version"]["id"]})).mappings().all()
        previous = ""
        for sequence, row in enumerate(rows, 1):
            assert row["sequence"] == sequence and row["prev_hash"] == previous
            canonical = json.dumps(row["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            previous = hashlib.sha256((previous + row["actor_id"] + row["action"] + row["version_id"] + canonical + row["created_at"].isoformat()).encode()).hexdigest()
            assert row["event_hash"] == previous
    initial = await loaded(live_api, draft)
    admin, _ = await admin_connection(json.loads(Path(os.environ["REALITY_DRAFT_MANIFEST"]).read_text()))
    try:
        await admin.execute("ALTER TABLE draft_audit_events ADD CONSTRAINT draft_audit_fault CHECK (action <> 'ResearchDraftSaved') NOT VALID")
        failed = await live_api.put(draft["route"] + "/draft", headers=draft["headers"], json=content())
        assert failed.status_code == 500
        assert await loaded(live_api, draft) == initial
        assert await admin.fetchval("SELECT count(*) FROM draft_audit_events WHERE version_id=$1", draft["version"]["id"]) == 5
        assert await admin.fetchval("SELECT count(*) FROM outbox_events WHERE version_id=$1", draft["version"]["id"]) == 5
    finally:
        await admin.execute("ALTER TABLE draft_audit_events DROP CONSTRAINT draft_audit_fault")
        await admin.close()


@pytest.mark.asyncio
async def test_replacement_primary_order_matches_reload_and_validation(live_api, pg, draft):
    payload = content()
    payload["equations"] = [{"label": label, "latex_raw": str(value), "canonical_ast_json": {"node_type": "constant", "value": value}} for label, value in (("A", 1), ("B", 9))]
    first = await saved(live_api, draft, payload)
    edit = from_snapshot(first)
    edit["equations"] = edit["equations"][1:]
    deleted = await saved(live_api, draft, edit)
    edit = from_snapshot(deleted)
    edit["equations"].insert(0, {"label": "C", "latex_raw": "5", "canonical_ast_json": {"node_type": "constant", "value": 5}})
    replaced = await saved(live_api, draft, edit)
    reloaded = await loaded(live_api, draft)
    assert reloaded == replaced
    assert [e["label"] for e in reloaded["equations"]] == ["C", "B"]
    assert reloaded["equations"][1]["id"] == first["equations"][1]["id"]
    run = await live_api.post(draft["route"] + "/validate", headers=draft["headers"])
    assert run.status_code == 200
    assert {finding["target_entity_id"] for finding in run.json()["findings"]} == {reloaded["equations"][0]["id"]}

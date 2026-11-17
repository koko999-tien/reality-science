"""Chromium UI -> live API -> real PostgreSQL; test-owned services and synthetic data."""
import asyncio
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import text

from tests.integration.test_decision3_postgres_rls import pg, live_api, context


@pytest.fixture(autouse=True)
def browser_cors(monkeypatch):
    # Process-local test API only; browser fetch uses no cookie credentials.
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", '["*"]')


@pytest.mark.asyncio
async def test_browser_create_edit_save_reload_and_conflict(live_api, pg, tmp_path):
    runtime = os.environ.get("REALITY_BROWSER_RUNTIME")
    if not runtime:
        pytest.skip("Explicit task-owned Playwright runtime required")
    sys.path.insert(0, runtime)
    from playwright.async_api import async_playwright, expect
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(NEXT_PUBLIC_API_URL=str(live_api.base_url).rstrip("/") + "/api/v1", NEXT_TELEMETRY_DISABLED="1")
    console_errors = []
    browser = None
    with (tmp_path / "frontend.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(["node", str(frontend / "node_modules/next/dist/bin/next"), "dev", "--hostname", "127.0.0.1", "--port", str(port)], cwd=frontend, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for _ in range(160):
                    assert server.poll() is None, "Frontend exited before ready"
                    try:
                        if (await client.get(origin + "/login", timeout=20)).status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    await asyncio.sleep(.25)
                else:
                    raise AssertionError("Frontend did not become ready")
            email = f"browser-{uuid.uuid4().hex}@example.com"
            password = secrets.token_urlsafe(24)
            registered = await live_api.post("/api/v1/iam/register", json={"email": email, "password": password, "display_name": "Draft browser fixture"})
            assert registered.status_code == 201
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                tab_context = await browser.new_context(viewport={"width": 1440, "height": 1000})
                page = await tab_context.new_page()
                page.on("pageerror", lambda error: console_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                try:
                    await page.goto(origin + "/login")
                    await page.wait_for_load_state("networkidle")
                    (tmp_path / "login-dom.txt").write_text(await page.locator("body").inner_text(), encoding="utf-8")
                    await page.get_by_label("Email Address").fill(email)
                    await page.get_by_label("Password", exact=True).fill(password)
                    await page.get_by_role("button", name="Authenticate", exact=True).click()
                    await page.wait_for_url("**/projects")
                    token = await page.evaluate("sessionStorage.getItem('reality-science.access-token')")
                    assert token
                    headers = {"Authorization": f"Bearer {token}"}
                    slug = "browser-draft-" + uuid.uuid4().hex
                    project = await live_api.post("/api/v1/projects", headers=headers, json={"slug": slug, "title": "Browser persistence fixture"})
                    assert project.status_code == 201
                    await page.goto(origin + f"/projects/{slug}/editor")
                    await page.wait_for_load_state("networkidle")
                    await expect(page.get_by_text("No version is recorded", exact=False)).to_be_visible()
                    (tmp_path / "empty-editor-dom.txt").write_text(await page.locator("body").inner_text(), encoding="utf-8")
                    await page.get_by_label("New draft title").fill("Browser-created draft")
                    await page.get_by_role("button", name="Create draft", exact=True).click()
                    await expect(page.get_by_label("Version", exact=True)).not_to_have_value("")
                    version_id = await page.get_by_label("Version", exact=True).input_value()
                    route = f"/api/v1/versions/{version_id}/draft"
                    # The rendered preset tile carries its title and an explicit Load button.
                    await page.get_by_role("heading", name="Kinetic Energy", exact=True).click()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_enabled()
                    await page.get_by_text("Custom unit definitions", exact=False).click()
                    await page.get_by_label("Unit name", exact=True).fill("browser_length")
                    await page.get_by_label("Unit symbol", exact=True).fill("brlen")
                    await page.get_by_label("Dimensionality", exact=True).fill("[length]")
                    await page.get_by_label("Scale factor", exact=True).fill("2.5")
                    await page.get_by_role("button", name="Add unit definition", exact=True).click()
                    await page.get_by_label("Variable symbol", exact=True).fill("probe")
                    await page.get_by_label("Variable name", exact=True).fill("Browser declaration")
                    await page.get_by_label("Physical SI unit", exact=True).fill("browser_length")
                    await page.get_by_role("button", name="Declare Symbol", exact=True).click()
                    await page.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_disabled()
                    saved = (await live_api.get(route, headers=headers)).json()
                    assert saved["units"][0]["scale_factor"] == 2.5
                    assert any(v["symbol"] == "probe" and v["unit"] == "browser_length" for v in saved["variables"])
                    assert saved["equations"][0]["canonical_ast_json"]["op"] == "*"
                    await page.reload()
                    await page.wait_for_load_state("networkidle")
                    await expect(page.get_by_label("Version", exact=True)).to_have_value(version_id)
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_disabled()
                    assert (await live_api.get(route, headers=headers)).json() == saved
                    await page.screenshot(path=str(tmp_path / "saved-reloaded.png"), full_page=True)
                    # Fresh physical connection confirms the UI-authored snapshot.
                    async with pg.begin() as old:
                        old_pid = (await old.execute(text("SELECT pg_backend_pid()"))).scalar_one()
                    await pg.dispose()
                    async with pg.begin() as fresh:
                        await context(fresh, project.json()["owner_actor_id"])
                        new_pid = (await fresh.execute(text("SELECT pg_backend_pid()"))).scalar_one()
                        assert new_pid != old_pid
                        row = (await fresh.execute(text("SELECT revision,units_json FROM research_versions WHERE id=:id"), {"id": version_id})).one()
                        assert row.revision == saved["version"]["revision"] and row.units_json == saved["units"]
                        assert (await fresh.execute(text("SELECT canonical_ast_json FROM equations WHERE version_id=:id"), {"id": version_id})).scalar_one() == saved["equations"][0]["canonical_ast_json"]
                        assert (await fresh.execute(text("SELECT unit FROM variables WHERE version_id=:id AND symbol='probe'"), {"id": version_id})).scalar_one() == "browser_length"
                    # Two independent tabs load the same revision; only one save wins.
                    tab2 = await tab_context.new_page()
                    await tab2.goto(origin + "/login")
                    await tab2.evaluate("token => sessionStorage.setItem('reality-science.access-token', token)", token)
                    tab2.on("dialog", lambda dialog: dialog.accept())
                    await tab2.goto(page.url)
                    await tab2.wait_for_load_state("networkidle")
                    constants = page.get_by_role("spinbutton", name=re.compile("Constant value for node"))
                    other_constants = tab2.get_by_role("spinbutton", name=re.compile("Constant value for node"))
                    await constants.first.fill("3")
                    await page.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_disabled()
                    winner = (await live_api.get(route, headers=headers)).json()
                    await other_constants.first.fill("4")
                    await tab2.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(tab2.get_by_role("alert").filter(has_text="newer revision")).to_be_visible()
                    await expect(other_constants.first).to_have_value("4")
                    assert (await live_api.get(route, headers=headers)).json() == winner
                    await tab2.screenshot(path=str(tmp_path / "two-tab-conflict.png"), full_page=True)
                    await tab2.get_by_role("button", name="Reload saved draft", exact=True).click()
                    await expect(other_constants.first).to_have_value("3")
                    # A transport failure retains pending edits and their revision.
                    await constants.first.fill("5")
                    await tab_context.set_offline(True)
                    await page.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(page.get_by_role("alert").filter(has_text="fetch")).to_be_visible()
                    await expect(constants.first).to_have_value("5")
                    await tab_context.set_offline(False)
                    assert (await live_api.get(route, headers=headers)).json() == winner
                    await page.get_by_role("button", name="Reload saved draft", exact=True).click()
                    await expect(constants.first).to_have_value("3")
                    # Actual worker finding becomes absent immediately on a semantic edit.
                    await page.get_by_role("button", name="Validate AST", exact=True).click()
                    await expect(page.get_by_test_id("finding-state-badge")).to_have_text("PASS", timeout=30000)
                    await constants.first.fill("6")
                    await expect(page.get_by_test_id("finding-state-badge")).to_have_text("NOT YET TESTED")
                    await page.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_disabled()
                    # Next client navigation / Back restores edits and the base revision.
                    await constants.first.fill("17")
                    await page.get_by_role("navigation", name="Main Navigation").get_by_role("link", name="Projects", exact=True).click()
                    await page.wait_for_url("**/projects")
                    await page.go_back()
                    await expect(constants.first).to_have_value("17")
                    await expect(page.get_by_text("Recovered unsaved edits", exact=False)).to_be_visible()
                    await page.get_by_role("button", name="Reload saved draft", exact=True).click()
                    await expect(constants.first).to_have_value("6")
                    # Version selector reloads the exact earlier ID after a newer draft exists.
                    await page.get_by_label("New draft title").fill("Second browser draft")
                    create_started = asyncio.Event()
                    release_create = asyncio.Event()
                    async def hold_creation(intercept):
                        if intercept.request.method == "POST":
                            create_started.set()
                            await release_create.wait()
                        await intercept.continue_()
                    await page.route("**/projects/" + slug + "/versions", hold_creation)
                    await page.get_by_role("button", name="Create draft", exact=True).click()
                    await asyncio.wait_for(create_started.wait(), 5)
                    await expect(constants.first).to_be_disabled()
                    assert await page.locator("fieldset").get_attribute("inert") is not None
                    release_create.set()
                    await expect(page.get_by_label("Version", exact=True)).not_to_have_value(version_id)
                    await page.unroute("**/projects/" + slug + "/versions", hold_creation)
                    await page.get_by_label("Version", exact=True).select_option(version_id)
                    await expect(constants.first).to_have_value("6")
                    # Declaration-only save preserves exact AST strings and authored LaTeX.
                    exact = (await live_api.get(route, headers=headers)).json()
                    authored = "\\underbrace{9007199254740993}_{\\text{authored}}"
                    exact_ast = {"node_type": "constant", "value": "9007199254740993"}
                    seeded = await live_api.put(route, headers=headers, json={"expected_revision": exact["version"]["revision"],
                        "equations": [{"id": exact["equations"][0]["id"], "label": "Exact", "latex_raw": authored, "canonical_ast_json": exact_ast}],
                        "variables": [], "units": []})
                    assert seeded.status_code == 200
                    await page.get_by_role("button", name="Reload saved draft", exact=True).click()
                    await expect(constants.first).to_have_value("9007199254740993")
                    await page.get_by_label("Variable symbol", exact=True).fill("only_declaration")
                    await page.get_by_label("Variable name", exact=True).fill("Unrelated declaration")
                    await page.get_by_label("Physical SI unit", exact=True).fill("meter")
                    await page.get_by_role("button", name="Declare Symbol", exact=True).click()
                    await page.get_by_role("button", name="Save draft", exact=True).click()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_be_disabled()
                    exact_saved = (await live_api.get(route, headers=headers)).json()
                    assert exact_saved["equations"][0]["canonical_ast_json"] == exact_ast
                    assert exact_saved["equations"][0]["latex_raw"] == authored
                    await page.reload()
                    await expect(constants.first).to_have_value("9007199254740993")
                    # DB freeze is fixture setup; UI must render the now immutable version read-only.
                    async with pg.begin() as conn:
                        await context(conn, project.json()["owner_actor_id"])
                        await conn.execute(text("UPDATE research_versions SET is_frozen=true WHERE id=:id"), {"id": version_id})
                    await page.reload()
                    await page.wait_for_load_state("networkidle")
                    await expect(page.get_by_text("This version is read-only.", exact=True)).to_be_visible()
                    await expect(constants.first).to_be_disabled()
                    await expect(page.get_by_role("button", name="Save draft", exact=True)).to_have_count(0)
                    await page.screenshot(path=str(tmp_path / "frozen-readonly.png"), full_page=True)
                    assert not console_errors, console_errors
                    (tmp_path / "browser-result.json").write_text(json.dumps({"status": "PASS", "browser": browser.version,
                        "origin": origin, "api_origin": str(live_api.base_url), "version_id": version_id,
                        "saved": saved, "winner_revision": winner["version"]["revision"],
                        "pg_pid_before": old_pid, "pg_pid_after": new_pid,
                        "checks": ["real UI login", "empty create", "AST/variable/custom unit save", "reload", "fresh DB read", "two-tab conflict", "offline preserves edits", "semantic edit clears finding", "client navigation recovery", "create authoring lock", "exact AST and authored LaTeX", "exact version selection", "frozen read-only"], "page_errors": console_errors}, indent=2), encoding="utf-8")
                except BaseException:
                    await page.screenshot(path=str(tmp_path / "failure.png"), full_page=True)
                    (tmp_path / "failure-dom.txt").write_text(await page.locator("body").inner_text(), encoding="utf-8")
                    raise
                finally:
                    await browser.close()
        finally:
            if server.poll() is None:
                subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"], capture_output=True, check=True)
            server.wait(timeout=15)
            with socket.socket() as sock:
                assert sock.connect_ex(("127.0.0.1", port)) != 0
            (tmp_path / "frontend-cleanup.json").write_text(json.dumps({"port": port, "exit": server.returncode, "closed": True}, indent=2))

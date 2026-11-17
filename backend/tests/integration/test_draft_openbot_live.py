"""Task-owned production UI/API/PG fixture, driven only by OpenBot private browser.

This test never launches a browser. Its loopback bridge bootstraps a synthetic
login and captures observations while retaining process handles for teardown.
"""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import asyncpg
import pytest
from sqlalchemy import text

from tests.integration.test_decision3_postgres_rls import pg, live_api, register_login, context


@pytest.fixture(autouse=True)
def browser_cors(monkeypatch):
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", '["*"]')


@pytest.mark.asyncio
async def test_openbot_browser_draft_acceptance(live_api, pg, tmp_path):
    if os.environ.get("REALITY_OPENBOT_BROWSER") != "1":
        pytest.skip("Requires explicit OpenBot private-browser driver")
    evidence = Path(os.environ["REALITY_OPENBOT_EVIDENCE"])
    headers, _ = await register_login(live_api)
    slug = "openbot-draft-" + uuid.uuid4().hex
    response = await live_api.post("/api/v1/projects", headers=headers,
        json={"slug": slug, "title": "OpenBot draft acceptance"})
    assert response.status_code == 201, response.text
    project = response.json()
    token = headers["Authorization"].removeprefix("Bearer ")
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    observations = []
    finished = threading.Event()

    async def freeze(version_id):
        conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("postgresql+asyncpg:", "postgresql:"))
        try:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_actor_id',$1,true)", project["owner_actor_id"])
                assert await conn.fetchval("SELECT project_id FROM research_versions WHERE id=$1", version_id) == project["id"]
                await conn.execute("UPDATE research_versions SET is_frozen=true WHERE id=$1", version_id)
        finally:
            await conn.close()

    class Bridge(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, data, status=200):
            encoded = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_OPTIONS(self):
            self.send_json({})

        def do_GET(self):
            if self.path == "/bootstrap":
                self.send_json({"token": token, "slug": slug, "api": str(live_api.base_url).rstrip("/")})
            else:
                self.send_json({"error": "unknown fixture route"}, 404)

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if self.path == "/record":
                assert "token" not in data
                observations.append(data)
                with (evidence / "browser-observations.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(data) + "\n")
                self.send_json({"recorded": len(observations)})
            elif self.path == "/freeze":
                asyncio.run(freeze(data["version_id"]))
                self.send_json({"frozen": data["version_id"]})
            elif self.path == "/finish":
                self.send_json({"finishing": True})
                finished.set()
            else:
                self.send_json({"error": "unknown fixture route"}, 404)

    bridge = ThreadingHTTPServer(("127.0.0.1", 0), Bridge)
    bridge_port = bridge.server_port
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    env = os.environ.copy()
    env.update(NEXT_PUBLIC_API_URL=str(live_api.base_url).rstrip("/") + "/api/v1", NEXT_TELEMETRY_DISABLED="1")
    server = build = None
    log = (tmp_path / "frontend.log").open("w", encoding="utf-8")
    try:
        with (evidence / "build-final-01.log").open("x", encoding="utf-8") as build_log:
            build = subprocess.Popen(["node", str(frontend / "node_modules/next/dist/bin/next"), "build"],
                cwd=frontend, env=env, stdout=build_log, stderr=subprocess.STDOUT)
            result = await asyncio.to_thread(build.wait, 300)
            assert result == 0, "Production build failed; inspect build-final-01.log"
        server = subprocess.Popen(["node", str(frontend / "node_modules/next/dist/bin/next"), "start",
            "--hostname", "127.0.0.1", "--port", str(port)], cwd=frontend, env=env, stdout=log, stderr=subprocess.STDOUT)
        import httpx
        async with httpx.AsyncClient() as client:
            deadline = time.monotonic() + 40
            while True:
                assert server.poll() is None
                try:
                    if (await client.get(origin + "/login", timeout=10)).status_code == 200:
                        break
                except httpx.RequestError:
                    pass
                assert time.monotonic() < deadline, "Frontend startup timeout"
                await asyncio.sleep(.15)
        (evidence / "browser-ready.json").write_text(json.dumps({"origin": origin,
            "api": str(live_api.base_url).rstrip("/"), "bridge": f"http://127.0.0.1:{bridge_port}",
            "slug": slug, "frontend_pid_handle": server.pid, "project": project}, indent=2))
        assert await asyncio.to_thread(finished.wait, 1800), "OpenBot browser acceptance deadline"
        assert observations and all(row["status"] == "PASS" for row in observations)
        required = {"create-save-reload", "two-tab-conflict", "failed-save-retains-edits",
                    "semantic-staleness", "navigation-recovery", "create-lock-selection",
                    "exact-ast-latex", "frozen-readonly"}
        assert required <= {row["check"] for row in observations}
        exact = next(row["snapshot"] for row in observations if row["check"] == "exact-ast-latex")
        async with pg.begin() as old:
            old_pid = (await old.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        await pg.dispose()
        async with pg.begin() as fresh:
            await context(fresh, project["owner_actor_id"])
            fresh_pid = (await fresh.execute(text("SELECT pg_backend_pid()"))).scalar_one()
            assert old_pid != fresh_pid
            version = (await fresh.execute(text("SELECT revision, units_json, is_frozen FROM research_versions WHERE id=:id"),
                {"id": exact["version"]["id"]})).one()
            equations = (await fresh.execute(text("SELECT canonical_ast_json,latex_raw FROM equations WHERE version_id=:id ORDER BY position"),
                {"id": exact["version"]["id"]})).all()
            assert version.revision == exact["version"]["revision"] and version.units_json == exact["units"]
            assert version.is_frozen
            assert equations[0].canonical_ast_json == exact["equations"][0]["canonical_ast_json"]
            assert equations[0].latex_raw == exact["equations"][0]["latex_raw"]
            variables = (await fresh.execute(text("SELECT symbol,unit FROM variables WHERE version_id=:id"),
                {"id": exact["version"]["id"]})).all()
            assert ("only_declaration", "meter") in variables
        (evidence / "browser-fresh-db.json").write_text(json.dumps({"status": "PASS", "old_pid": old_pid,
            "fresh_pid": fresh_pid, "version_id": exact["version"]["id"], "revision": version.revision,
            "checks": sorted(required), "observations": len(observations)}, indent=2))
    finally:
        bridge.shutdown()
        bridge.server_close()
        for process in (server, build):
            if process and process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=True, capture_output=True)
                process.wait(timeout=20)
        log.close()
        closed = {}
        for listener in (port, bridge_port):
            with socket.socket() as sock:
                closed[str(listener)] = sock.connect_ex(("127.0.0.1", listener)) != 0
        (evidence / "browser-ui-cleanup.json").write_text(json.dumps({"closed": closed,
            "frontend_exit": server.returncode if server else None, "build_exit": build.returncode if build else None}, indent=2))
        assert all(closed.values())

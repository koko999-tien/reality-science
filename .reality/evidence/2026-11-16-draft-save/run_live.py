"""Reuse the verified queue lifecycle, with draft migration and distinct evidence."""
import asyncio
import importlib.util
import json
import os
import ast
import hashlib
from pathlib import Path
import sys

E = Path(__file__).resolve().parent
ROOT = E.parents[2]
spec = importlib.util.spec_from_file_location("verified_queue_lifecycle", E.parent / "2026-11-16-compute-queue/run_live.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)
queue.E = E
from scripts.disposable_postgres import execute, environment, admin_connection, grant_app


async def identity(manifest):
    conn, actual = await admin_connection(manifest)
    try:
        actual["revision"] = (await conn.fetchval("SELECT version_num FROM alembic_version")
                              if await conn.fetchval("SELECT to_regclass('public.alembic_version')") else None)
        # Ownership is established by admin_connection, independently of schema.
        actual["app_role"] = dict(await conn.fetchrow("SELECT rolname,rolsuper,rolbypassrls FROM pg_roles WHERE rolname='rs_test_app'"))
        assert not actual["app_role"]["rolsuper"] and not actual["app_role"]["rolbypassrls"]
        return actual
    finally:
        await conn.close()


original_start = queue.start_cluster


def start_and_migrate(manifest, manifest_path, evidence):
    original_start(manifest, manifest_path, evidence)
    env = environment(manifest)
    env["DATABASE_URL"] = env["DATABASE_URL"].replace("rs_test_app@", "rs_test_admin@")
    if execute([sys.executable, "-m", "alembic", "upgrade", "head"], evidence / "migrate.log", env):
        raise RuntimeError("Draft migration failed")
    asyncio.run(grant_app(manifest))
    # Record final schema directly after Alembic; no function replacement.
    async def record_fixture_schema():
        source = ROOT / "backend/app/db/migrations/versions/005_atomic_drafts.py"
        conn, identity = await admin_connection(manifest)
        try:
            definition = await conn.fetchval("SELECT pg_get_functiondef('fn_math_content_revision()'::regprocedure)")
            assert await conn.fetchval("SELECT count(*) FROM information_schema.columns WHERE table_name='equations' AND column_name='position'") == 1
            assert await conn.fetchval("SELECT count(*) FROM information_schema.columns WHERE table_name='draft_audit_events' AND column_name='sequence'") == 1
            (evidence / "fixture-schema.json").write_text(json.dumps({"identity": identity,
                "migration_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "math_trigger": definition, "equation_position": True, "audit_sequence": True}, indent=2))
        finally:
            await conn.close()
    asyncio.run(record_fixture_schema())


queue.start_cluster = start_and_migrate
queue.identity = identity
if __name__ == "__main__":
    # Only copy a manifest explicitly naming the checked, clean synthetic cluster.
    manifest = E / "instance.json"
    if not manifest.exists():
        source = E.parent / "2026-11-17-review-fixes/instance.json"
        data = json.loads(source.read_text())
        assert data["stopped"] and data["system_id"] == "7708747722773675460"
        with manifest.open("x") as stream:
            json.dump(data, stream, indent=2)
    os.environ["REALITY_DRAFT_MANIFEST"] = str(manifest)
    raise SystemExit(queue.main())

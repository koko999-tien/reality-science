import pytest
from sqlalchemy.engine import URL
from unittest.mock import AsyncMock, MagicMock

from tests.postgres_target import UnsafePostgresTarget, disposable_target, verify_disposable_connection


INSTANCE = "1234567890abcdef1234567890abcdef"


def target_env(**overrides):
    fields = dict(drivername="postgresql+asyncpg", username="rs_test_app",
                  host="127.0.0.1", port=55437, database=f"rs_test_{INSTANCE}")
    fields.update(overrides)
    return {"REALITY_TEST_DATABASE_URL": URL.create(**fields).render_as_string(hide_password=False),
            "REALITY_TEST_INSTANCE_ID": INSTANCE}


def test_default_never_uses_application_or_legacy_url():
    assert disposable_target({}) is None
    assert disposable_target({"DATABASE_URL": "ignored", "TEST_DATABASE_URL": "ignored"}) is None


@pytest.mark.parametrize("overrides", [
    {"host": "localhost"}, {"host": "db.example.com"}, {"host": "192.168.1.2"},
    {"port": None}, {"port": 5432}, {"port": 80},
    {"database": "reality_science"}, {"database": "rs_test_other"},
    {"username": "postgres"}, {"drivername": "sqlite"},
    {"query": {"host": "remote"}},
])
def test_unsafe_targets_rejected_before_connection(overrides):
    with pytest.raises(UnsafePostgresTarget):
        disposable_target(target_env(**overrides))


@pytest.mark.parametrize("env", [
    {"REALITY_TEST_DATABASE_URL": "bad"},
    {"REALITY_TEST_INSTANCE_ID": INSTANCE},
    {"REALITY_TEST_DATABASE_URL": "bad", "REALITY_TEST_INSTANCE_ID": INSTANCE},
    {"REALITY_TEST_DATABASE_URL": "bad", "REALITY_TEST_INSTANCE_ID": "wrong"},
])
def test_partial_or_invalid_opt_in_rejected(env):
    with pytest.raises(UnsafePostgresTarget):
        disposable_target(env)


def test_explicit_disposable_target_accepted():
    target = disposable_target(target_env())
    assert target.instance_id == INSTANCE
    assert target.url.port == 55437


def test_guard_errors_do_not_echo_url_credentials():
    with pytest.raises(UnsafePostgresTarget) as exc:
        disposable_target(target_env(host="remote", password="example-not-a-real-secret"))
    assert "example-not-a-real-secret" not in str(exc.value)


def connected_fixture(**changes):
    row = dict(database=f"rs_test_{INSTANCE}", role="rs_test_app", host="127.0.0.1", port=55437,
               cluster=f"rs_test_{INSTANCE}", version="17.12", database_owner="rs_test_admin",
               rolsuper=False, rolbypassrls=False, rolcreatedb=False, rolcreaterole=False,
               has_memberships=False, owns_tables=False)
    row.update(changes)
    identity, marker = MagicMock(), MagicMock()
    identity.mappings.return_value.one.return_value = row
    marker.scalars.return_value.all.return_value = [INSTANCE]
    return AsyncMock(execute=AsyncMock(side_effect=[identity, marker])), marker


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [
    {"database": "reality_science"}, {"role": "rs_test_admin"}, {"database_owner": "rs_test_app"},
    {"host": "192.168.1.1"}, {"port": 5432}, {"cluster": "different-instance"},
    {"rolsuper": True}, {"rolbypassrls": True}, {"rolcreatedb": True}, {"rolcreaterole": True},
    {"has_memberships": True}, {"owns_tables": True},
])
async def test_connected_target_mismatch_stops_before_fixture_writes(changes):
    connection, _ = connected_fixture(**changes)
    with pytest.raises(UnsafePostgresTarget):
        await verify_disposable_connection(connection, disposable_target(target_env()))
    assert connection.execute.await_count == 1
    assert str(connection.execute.call_args.args[0]).strip().startswith("SELECT")


@pytest.mark.asyncio
@pytest.mark.parametrize("markers", [[], ["different-instance"], [INSTANCE, INSTANCE]])
async def test_connected_marker_mismatch_rejected(markers):
    connection, marker = connected_fixture()
    marker.scalars.return_value.all.return_value = markers
    with pytest.raises(UnsafePostgresTarget, match="marker mismatch"):
        await verify_disposable_connection(connection, disposable_target(target_env()))
    assert all(str(call.args[0]).strip().startswith("SELECT") for call in connection.execute.call_args_list)


@pytest.mark.asyncio
async def test_matching_connected_target_accepted():
    connection, _ = connected_fixture()
    identity = await verify_disposable_connection(connection, disposable_target(target_env()))
    assert identity["role"] == "rs_test_app"
    assert connection.execute.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("configured", [None, "invalid", "partial"])
async def test_live_fixture_never_creates_engine_without_valid_opt_in(monkeypatch, configured):
    from tests.integration import test_decision3_postgres_rls as live

    monkeypatch.delenv("REALITY_TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("REALITY_TEST_INSTANCE_ID", raising=False)
    monkeypatch.setenv("DATABASE_URL", "application-url-must-not-be-used")
    monkeypatch.setenv("TEST_DATABASE_URL", "legacy-url-must-not-be-used")
    if configured:
        monkeypatch.setenv("REALITY_TEST_DATABASE_URL", target_env(host="remote.example")["REALITY_TEST_DATABASE_URL"])
        if configured == "invalid":
            monkeypatch.setenv("REALITY_TEST_INSTANCE_ID", INSTANCE)
    engine_factory = MagicMock(side_effect=AssertionError("Must not create an engine"))
    monkeypatch.setattr(live, "create_async_engine", engine_factory)
    fixture = live.pg.__wrapped__()
    try:
        expected = UnsafePostgresTarget if configured else pytest.skip.Exception
        with pytest.raises(expected):
            await anext(fixture)
    finally:
        await fixture.aclose()
    engine_factory.assert_not_called()

"""Fail closed before starting or mutating an incorrectly identified cluster."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import disposable_postgres as runner


@pytest.fixture
def manifest(tmp_path):
    token = "a" * 32
    data = tmp_path / "data"
    data.mkdir()
    return {"instance_id": token, "database": f"rs_test_{token}", "port": 60655,
            "data": str(data), "bin": str(tmp_path / "pgsql/bin"), "stopped": True,
            "system_id": "1234567890", "postmaster_pid": 99999}


@pytest.mark.parametrize("change", [
    {"instance_id": "invalid"}, {"database": "reality_science"},
    {"port": 5432}, {"port": "60655"}, {"data": "relative/data"},
])
@pytest.mark.asyncio
async def test_bad_manifest_does_not_connect(manifest, monkeypatch, change):
    manifest.update(change)
    connect = AsyncMock()
    monkeypatch.setattr(runner.asyncpg, "connect", connect)
    with pytest.raises(RuntimeError):
        await runner.admin_connection(manifest)
    connect.assert_not_called()


@pytest.mark.parametrize("fault", ["not_stopped", "missing_identity", "pid_marker", "wrong_identity", "unclean"])
def test_restart_rejects_unsafe_offline_state_before_config_or_socket(manifest, monkeypatch, fault):
    from pathlib import Path

    control = {"Database system identifier": manifest["system_id"], "Database cluster state": "shut down"}
    if fault == "not_stopped":
        manifest["stopped"] = False
    elif fault == "missing_identity":
        manifest.pop("system_id")
    elif fault == "pid_marker":
        (Path(manifest["data"]) / "postmaster.pid").write_text("untrusted stale or live pid")
    elif fault == "wrong_identity":
        control["Database system identifier"] = "other-cluster"
    else:
        control["Database cluster state"] = "in production"
    monkeypatch.setattr(runner, "control_data", lambda _: control)
    read_config = MagicMock(side_effect=AssertionError("Should not inspect config"))
    socket_factory = MagicMock(side_effect=AssertionError("Should not open socket"))
    monkeypatch.setattr(runner.subprocess, "check_output", read_config)
    monkeypatch.setattr(runner.socket, "socket", socket_factory)
    with pytest.raises(RuntimeError):
        runner.verify_stopped_cluster(manifest)
    read_config.assert_not_called()
    socket_factory.assert_not_called()


@pytest.mark.parametrize("setting", ["data_directory", "port", "listen_addresses", "cluster_name"])
def test_restart_rejects_config_redirect_before_port_check(manifest, monkeypatch, setting):
    control = {"Database system identifier": manifest["system_id"], "Database cluster state": "shut down"}
    config = {"data_directory": manifest["data"], "port": str(manifest["port"]),
              "listen_addresses": "127.0.0.1", "cluster_name": manifest["database"]}
    config[setting] = "incorrect"
    monkeypatch.setattr(runner, "control_data", lambda _: control)
    monkeypatch.setattr(runner.subprocess, "check_output", lambda command, **_: config[command[-1]])
    socket_factory = MagicMock(side_effect=AssertionError("Should not open socket"))
    monkeypatch.setattr(runner.socket, "socket", socket_factory)
    with pytest.raises(RuntimeError, match="configuration mismatch"):
        runner.verify_stopped_cluster(manifest)
    socket_factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["system_id", "port", "marker", "missing_marker_table"])
async def test_online_identity_or_marker_failure_closes_connection(manifest, monkeypatch, fault):
    identity = {"data": manifest["data"], "cluster": manifest["database"],
                "system_id": manifest["system_id"], "database": manifest["database"],
                "role": "rs_test_admin", "host": "127.0.0.1", "port": manifest["port"]}
    if fault in identity:
        identity[fault] = "incorrect"
    conn = AsyncMock()
    conn.fetchrow.return_value = identity
    conn.fetch.return_value = [{"instance_id": "incorrect" if fault == "marker" else manifest["instance_id"]}]
    if fault == "missing_marker_table":
        conn.fetch.side_effect = RuntimeError("marker table absent")
    monkeypatch.setattr(runner.asyncpg, "connect", AsyncMock(return_value=conn))
    with pytest.raises(RuntimeError):
        await runner.admin_connection(manifest)
    conn.close.assert_awaited_once()
    conn.execute.assert_not_called()


@pytest.mark.parametrize("outcome", ["success", "marker_failure", "pid_read_failure", "identity_failure"])
def test_restart_lifecycle_records_current_pid_and_cleans_failed_verification(manifest, monkeypatch, tmp_path, outcome):
    manifest_path = tmp_path / "instance.json"
    marker = Path(manifest["data"]) / "postmaster.pid"
    commands = []
    monkeypatch.setattr(runner, "verify_stopped_cluster", lambda _: {"verified": True})

    def execute(command, *_):
        commands.append(command[-1])
        saved = json.loads(manifest_path.read_text())
        assert saved["stopped"] is False
        if command[-1] == "start":
            assert "postmaster_pid" not in saved  # historical PID was discarded before launch
            marker.write_text("task test marker")
        else:
            assert saved["postmaster_pid"] == 1234
            marker.unlink()
        return 0

    monkeypatch.setattr(runner, "execute", execute)
    pid = MagicMock(return_value=1234)
    if outcome == "pid_read_failure":
        pid.side_effect = [RuntimeError("PID temporarily unreadable"), 1234, 1234]
    monkeypatch.setattr(runner, "current_postmaster", pid)
    connection = AsyncMock()
    admin = AsyncMock(return_value=(connection, {"system_id": manifest["system_id"]}))
    if outcome in ("marker_failure", "identity_failure"):
        admin.side_effect = RuntimeError("Online verification failed")
    cluster = AsyncMock(return_value=(connection, {"system_id": manifest["system_id"]}))
    if outcome == "identity_failure":
        cluster.side_effect = RuntimeError("Server identity mismatch")
    monkeypatch.setattr(runner, "admin_connection", admin)
    monkeypatch.setattr(runner, "cluster_connection", cluster)
    clean = MagicMock()
    monkeypatch.setattr(runner, "verify_clean_shutdown", clean)

    if outcome == "success":
        assert runner.start_cluster(manifest, manifest_path, tmp_path) == 0
    else:
        with pytest.raises(RuntimeError):
            runner.start_cluster(manifest, manifest_path, tmp_path)
    saved = json.loads(manifest_path.read_text())
    assert saved["postmaster_pid"] == 1234
    if outcome in ("marker_failure", "pid_read_failure"):
        assert commands == ["start", "stop"]
        assert saved["stopped"] is True and saved["lifecycle_state"] == "stopped"
        assert not marker.exists()
        cluster.assert_awaited_once()
        clean.assert_called_once()
    else:
        assert commands == ["start"]
        assert saved["stopped"] is False
        assert saved["lifecycle_state"] == ("running" if outcome == "success" else "cleanup_required")
        clean.assert_not_called()

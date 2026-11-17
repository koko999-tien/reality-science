"""Failure-path checks for the local-only PostgreSQL/queue evidence runner."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def runner(monkeypatch, tmp_path):
    path = ROOT / '.reality/evidence/2026-11-16-compute-queue/run_live.py'
    spec = importlib.util.spec_from_file_location('queue_lifecycle_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'E', tmp_path)
    return module


@pytest.mark.skipif(os.name != 'nt', reason='The local evidence harness uses Windows taskkill')
def test_timeout_stops_live_parent_and_its_listener_descendant(runner, tmp_path, monkeypatch):
    """Real child listener; deliberately no Python/pytest teardown to rescue it."""
    child = tmp_path / 'listener.py'
    child.write_text(
        'import json, os, socket, sys, time\n'
        'from pathlib import Path\n'
        'with socket.socket() as s:\n'
        '    s.bind(("127.0.0.1", 0)); s.listen()\n'
        '    Path(sys.argv[1]).write_text(json.dumps({"pid": os.getpid(), "port": s.getsockname()[1]}))\n'
        '    time.sleep(60)\n'
    )
    parent = tmp_path / 'parent.py'
    parent.write_text(
        'import subprocess, sys, time\n'
        'subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n'
        'time.sleep(60)\n'
    )
    marker = tmp_path / 'listener.json'
    owned = []
    original = runner.stop_owned_process

    def stop(process):
        owned.append((process, process.poll()))
        original(process)

    monkeypatch.setattr(runner, 'stop_owned_process', stop)
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run([sys.executable, str(parent), str(child), str(marker)], 'timeout-tree', os.environ.copy(), timeout=3)
    assert len(owned) == 1 and owned[0][1] is None, 'Parent must still be alive when tree cleanup starts'
    assert owned[0][0].poll() is not None
    identity = json.loads(marker.read_text())
    with socket.socket() as sock:
        sock.settimeout(.5)
        assert sock.connect_ex(('127.0.0.1', identity['port'])) != 0


@pytest.mark.parametrize('fault', ['worker', 'info', 'shutdown', 'wait', 'client-close', 'identity', 'postgres', 'log-close'])
def test_each_cleanup_failure_still_attempts_remaining_resources(runner, monkeypatch, tmp_path, fault):
    events = []
    worker = SimpleNamespace(pid=123, returncode=None)
    worker.poll = lambda: worker.returncode
    broker = SimpleNamespace(pid=124, returncode=None)
    broker.poll = lambda: broker.returncode
    manifest = {'stopped': False, 'port': 60001}

    def event(name):
        events.append(name)
        if name == fault:
            raise RuntimeError('injected ' + name)

    def stop(process):
        event('worker' if process is worker else 'broker-process')
        process.returncode = 1

    def info(section):
        event('info')
        return {'run_id': 'owned'}

    def shutdown(**kwargs):
        event('shutdown')

    def wait(**kwargs):
        event('wait')
        broker.returncode = 0

    async def identity(unused):
        event('identity')

    def stop_cluster(unused, log):
        event('postgres')
        manifest['stopped'] = True
        return 0

    broker.wait = wait
    client = SimpleNamespace(info=info, get=lambda key: 'fault-owned', shutdown=shutdown,
                             close=lambda: event('client-close'))
    log = SimpleNamespace(close=lambda: event('log-close'))
    monkeypatch.setattr(runner, 'stop_owned_process', stop)
    monkeypatch.setattr(runner, 'identity', identity)
    monkeypatch.setattr(runner, 'stop_cluster', stop_cluster)
    monkeypatch.setattr(runner, 'control_data', lambda unused: {'state': 'mocked'})
    sock = Mock()
    sock.__enter__ = Mock(return_value=sock)
    sock.__exit__ = Mock(return_value=False)
    sock.connect_ex.return_value = 1
    # Replace only the runner's reference; asyncio needs the real socket module.
    monkeypatch.setattr(runner, 'socket', SimpleNamespace(socket=lambda: sock))
    with pytest.raises(RuntimeError, match='Cleanup failures'):
        runner.cleanup_resources('fault', manifest, tmp_path / 'manifest.json', worker, broker,
                                 client, 'owned', 60002, [log], {})
    assert 'client-close' in events and 'identity' in events and 'log-close' in events
    if fault != 'identity':
        assert 'postgres' in events
    else:
        assert 'postgres' not in events, 'Failed ownership verification must prevent shutdown'
    assert broker.poll() is not None
    evidence = json.loads((tmp_path / 'fault-cleanup.json').read_text())
    assert evidence['errors']
    assert any('injected ' + fault in item['message'] for item in evidence['errors'])
    assert json.loads((tmp_path / 'manifest.json').read_text()) == manifest


def test_multiple_failures_are_recorded_before_raising(runner, monkeypatch, tmp_path):
    class FailingLog:
        def close(self):
            raise OSError('injected log')

    async def wrong_identity(unused):
        raise RuntimeError('injected identity')

    monkeypatch.setattr(runner, 'identity', wrong_identity)
    monkeypatch.setattr(runner, 'control_data', lambda unused: {})
    stop = Mock()
    monkeypatch.setattr(runner, 'stop_cluster', stop)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with pytest.raises(RuntimeError, match='postgres.*log-0.*verification'):
        runner.cleanup_resources('many', {'stopped': False, 'port': port}, tmp_path / 'manifest.json',
                                 None, None, None, None, None, [FailingLog()], {})
    stop.assert_not_called()
    evidence = json.loads((tmp_path / 'many-cleanup.json').read_text())
    assert {'postgres', 'log-0', 'verification'} <= {error['stage'] for error in evidence['errors']}

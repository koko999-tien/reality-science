"""Run a real lifecycle with a bounded, explicitly named teardown failure."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('D:/Reality_Science')
E = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
spec = importlib.util.spec_from_file_location(
    'live_fault_runner', ROOT / '.reality/evidence/2026-11-16-compute-queue/run_live.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.E = E
mode = sys.argv[1]
assert mode in {'live-cleanup-redis-fault', 'live-cleanup-pytest-timeout'}
assert not (E / (mode + '-fault-check.json')).exists()
sys.argv = [sys.argv[0], mode,
            'tests/integration/test_compute_queue_live.py::test_interactive_uses_real_queue[valid-PASS]']

if mode == 'live-cleanup-redis-fault':
    class FaultRedis(runner.Redis):
        def shutdown(self, **kwargs):
            assert self.get('reality-test-instance').startswith(mode + '-')
            raise ConnectionError('injected task-owned Redis shutdown failure')

    runner.Redis = FaultRedis
else:
    original_run = runner.run

    def timeout_run(command, name, env):
        env = env.copy()
        env['PYTHONPATH'] = os.pathsep.join([str(E), env.get('PYTHONPATH', '')])
        env['REALITY_TEST_OUTER_TIMEOUT_MARKER'] = str(E / (mode + '-probe.json'))
        return original_run([*command, '-p', 'live_timeout_probe'], name, env, timeout=30)

    runner.run = timeout_run

try:
    runner.main()
except Exception as error:
    caught = {'type': type(error).__name__, 'message': str(error)}
    if mode == 'live-cleanup-redis-fault':
        assert isinstance(error, RuntimeError) and str(error) == 'Cleanup failures: broker-shutdown'
    else:
        assert isinstance(error, subprocess.TimeoutExpired)
else:
    raise AssertionError('Deliberate lifecycle failure was not observed')

cleanup = json.loads((E / (mode + '-cleanup.json')).read_text())
assert cleanup['postgres_stopped'] is True
assert cleanup['postgres_control']['Database cluster state'] == 'shut down'
assert all(value is False for value in cleanup['ports_accepting'].values())
assert cleanup['worker_exit'] is not None and cleanup['broker_exit'] is not None
if mode == 'live-cleanup-redis-fault':
    assert cleanup['codes']['tests']['exit'] == 0
    assert [error['stage'] for error in cleanup['errors']] == ['broker-shutdown']
    assert cleanup['errors'][0]['message'] == 'injected task-owned Redis shutdown failure'
else:
    assert cleanup['errors'] == []
    probe = json.loads((E / (mode + '-probe.json')).read_text())
    assert probe['real_api_test_body_passed'] is True
    assert probe['api_fixture_still_active'] is True
    assert len(cleanup['ports_accepting']) >= 3

result = {'status': 'PASS', 'mode': mode, 'expected_failure': caught,
          'postgres_stopped': True, 'recorded_ports_closed': True,
          'worker_exited': True, 'broker_exited': True,
          'cleanup_error_stages': [error['stage'] for error in cleanup['errors']]}
with (E / (mode + '-fault-check.json')).open('x', encoding='utf-8') as output:
    json.dump(result, output, indent=2)
print(json.dumps(result, indent=2))

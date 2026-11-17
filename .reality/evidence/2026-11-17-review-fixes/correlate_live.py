"""Fail-closed read-only correlation of completed live fault evidence."""
import json
from pathlib import Path

E = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def check(mode):
    assert read_json(E / (mode + '-exit.json'))['exit'] == 0
    api_paths = list((E / (mode + '-pytest')).glob('*/soft-deadline-evidence.json'))
    # pytest can expose a "current" directory junction to the same evidence.
    api_paths = sorted({path.resolve() for path in api_paths})
    assert len(api_paths) == 1, api_paths
    api = read_json(api_paths[0])
    injections = lines(E / (mode + '-injection.jsonl'))
    results = lines(E / (mode + '-worker-results.jsonl'))
    worker = read_json(E / (mode + '-worker-identity.json'))
    broker = read_json(E / (mode + '-broker-identity.json'))
    cleanup = read_json(E / (mode + '-cleanup.json'))
    assert len(injections) == len(results) == 1
    injected, result = injections[0], results[0]
    assert injected['mode'] == mode
    assert injected['exception'] == 'SoftTimeLimitExceeded'
    assert injected['pid'] == worker['pid']
    assert injected['job_id'] == result['job_id']
    assert result['version_id'] == api['version_id']
    assert result['target_entity_id'] == api['target_id']
    assert result['target_entity_type'] == 'EQUATION'
    assert result['state'] == 'NEEDS_EXPERT_REVIEW'
    assert result['diagnostic_code'] == 'COMPUTE_TIMEOUT_EXCEEDED'
    assert result['dimensions_verified'] is False
    assert len(result['bundle_sha256']) == 64
    assert api['http_status'] == 503
    assert api['persisted_runs'] == api['persisted_findings'] == 0
    assert api['publication_preserved'] == 'preprint'
    assert worker['database_env_guard'] == 'PASS'
    assert worker['database_drivers_present'] == []
    connections = lines(E / (mode + '-worker-connections.jsonl'))
    assert connections
    port = broker['server']['tcp_port']
    assert all(item['pid'] == worker['pid'] and item['address'] == ['127.0.0.1', port]
               for item in connections)
    assert cleanup['errors'] == []
    assert cleanup['postgres_stopped'] is True
    assert cleanup['postgres_control']['Database cluster state'] == 'shut down'
    assert all(value is False for value in cleanup['ports_accepting'].values())
    assert cleanup['worker_exit'] is not None and cleanup['broker_exit'] is not None
    return {
        'status': 'PASS', 'mode': mode, 'job_id': result['job_id'],
        'version_id': result['version_id'], 'target_entity_id': result['target_entity_id'],
        'bundle_sha256': result['bundle_sha256'], 'worker_pid_historical': worker['pid'],
        'state': result['state'], 'diagnostic_code': result['diagnostic_code'],
        'http_status': api['http_status'], 'persisted_runs': 0, 'persisted_findings': 0,
        'publication': api['publication_preserved'], 'worker_database_env_guard': 'PASS',
        'database_drivers_present': [], 'observed_worker_connects_only_to_owned_redis': True,
        'clean_shutdown_verified': True, 'native_timer_delivery': 'NOT RUN',
        'api_evidence': str(api_paths[0].relative_to(E)),
    }


if __name__ == '__main__':
    results = [check(mode) for mode in ('soft-dimensions', 'soft-limit')]
    with (E / 'live-correlation.json').open('x', encoding='utf-8') as output:
        json.dump(results, output, indent=2)
    print(json.dumps(results, indent=2))

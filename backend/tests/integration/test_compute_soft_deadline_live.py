"""Real API/queue/DB with a deliberately injected worker helper deadline.

Windows solo cannot deliver a prefork soft signal. The separate evidence
bootstrap injects the real exception; all transport and persistence are real.
"""
import json
import os

import pytest
from sqlalchemy import text

from tests.integration.test_decision3_postgres_rls import pg, live_api, context
from tests.integration.test_compute_queue_live import (
    require_owned_queue, assert_queue_identity, seed_version, assert_no_persisted_run,
)


@pytest.mark.asyncio
async def test_helper_soft_deadline_is_rejected_without_persistence(live_api, pg, tmp_path):
    mode = os.environ.get('REALITY_TEST_SOFT_DEADLINE')
    if mode not in {'dimensions', 'limit'}:
        pytest.skip('Explicit fault-injecting worker lifecycle required')
    await assert_queue_identity()
    headers, actor, version = await seed_version(pg, live_api)
    route = f'/api/v1/versions/{version}'
    equation = await live_api.post(route + '/equations', headers=headers, json={
        'label': 'Deadline fixture', 'latex_raw': 'x',
        'canonical_ast_json': {'node_type': 'variable', 'value': 'x'},
    })
    assert equation.status_code == 201, equation.text
    variable = await live_api.post(route + '/variables', headers=headers, json={
        'symbol': 'x', 'name': 'position', 'unit': 'm',
    })
    assert variable.status_code == 201, variable.text
    response = await live_api.post(route + '/validate', headers=headers)
    assert response.status_code == 503, response.text
    await assert_no_persisted_run(live_api, pg, headers, actor, version)
    async with pg.begin() as connection:
        await context(connection, actor)
        count = (await connection.execute(text(
            'SELECT count(*) FROM validation_findings WHERE target_entity_id=:id'
        ), {'id': equation.json()['id']})).scalar_one()
        assert count == 0
    (tmp_path / 'soft-deadline-evidence.json').write_text(json.dumps({
        'injected_exception': 'SoftTimeLimitExceeded', 'helper': mode,
        'version_id': version, 'target_id': equation.json()['id'],
        'http_status': response.status_code, 'persisted_runs': 0, 'persisted_findings': count,
        'publication_preserved': 'preprint',
    }, indent=2))

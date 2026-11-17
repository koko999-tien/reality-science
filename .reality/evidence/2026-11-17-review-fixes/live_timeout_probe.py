"""Opt-in pytest hook: keep the API fixture alive after a successful real call."""
import json
import os
from pathlib import Path
import time

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    marker = os.environ.get('REALITY_TEST_OUTER_TIMEOUT_MARKER')
    if marker and outcome.excinfo is None:
        Path(marker).write_text(json.dumps({
            'pid': os.getpid(), 'test': item.nodeid,
            'real_api_test_body_passed': True, 'api_fixture_still_active': True,
        }, indent=2))
        # The evidence harness must kill this owned pytest/API tree; its timeout
        # is shorter than this hook, so normal fixture teardown cannot rescue it.
        time.sleep(90)

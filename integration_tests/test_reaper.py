from functools import partial
import subprocess
import sys
import time

import psutil
import pytest

import client
import integration_tests.common


pytestmark = pytest.mark.needs_build


@pytest.fixture(scope='function', params=[2, 3, 4])
def get_connections_and_wait(request):
    server, process = integration_tests.common.start_server([
        'integration_tests/reaper.py', '1', str(request.param)], path='.test',
        return_process=True)

    yield lambda: len(process.connections()), partial(time.sleep, request.param)

    server.terminate()
    assert server.wait() == 0


def test_empty(get_connections_and_wait):
    get_connections, wait = get_connections_and_wait
    conn = client.Connection('localhost:8080')

    assert get_connections() == 1

    conn.maybe_connect()
    time.sleep(.1)

    assert get_connections() == 2

    wait()

    assert get_connections() == 1


def test_request(get_connections_and_wait):
    get_connections, wait = get_connections_and_wait
    conn = client.Connection('localhost:8080')

    assert get_connections() == 1

    conn.putrequest('GET', '/')
    conn.endheaders()

    assert get_connections() == 2

    wait()
    time.sleep(1)
    
    assert get_connections() == 1

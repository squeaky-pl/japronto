import pytest
import subprocess
import time

import client
import integration_tests.common


pytestmark = pytest.mark.needs_build


@pytest.fixture(scope='function')
def server():
    return integration_tests.common.start_server(
        'integration_tests/drain.py', stdout=subprocess.PIPE, path='.test')


@pytest.fixture(scope='function')
def server_terminate(server):
    def terminate():
        server.terminate()
        assert server.wait() == 0

        stdout = server.stdout.read()

        return [l.decode('utf-8').strip() for l in stdout.splitlines()]

    yield terminate

    server.terminate()


@pytest.fixture(scope='function')
def connect():
    connections = []

    def _connect():
        conn = client.Connection('localhost:8080')
        conn.maybe_connect()

        connections.append(conn)

        return conn

    yield _connect

    for c in connections:
        c.close()


def test_no_connections(server_terminate):
    lines = server_terminate()

    assert lines[-1] == 'Termination request received'


@pytest.mark.parametrize('num', range(1, 5))
def test_unclosed_connections(num, connect, server_terminate):
    for _ in range(num):
        connect()

    lines = server_terminate()

    assert lines[-1] == '{} idle connections closed immediately'.format(num)


@pytest.mark.parametrize('num', range(1, 5))
def test_closed_connections(num, connect, server_terminate):
    for _ in range(num):
        con = connect()
        con.close()

    lines = server_terminate()

    assert lines[-1] == 'Termination request received'


@pytest.mark.parametrize('num', range(1, 5))
def test_unclosed_requests(num, connect, server_terminate):
    for _ in range(num):
        con = connect()
        con.putrequest('GET', '/')
        con.endheaders()

    lines = server_terminate()

    assert lines[-1] == '{} idle connections closed immediately'.format(num)


@pytest.mark.parametrize('num', range(1, 5))
def test_closed_requests(num, connect, server_terminate):
    for _ in range(num):
        con = connect()
        con.putrequest('GET', '/')
        con.endheaders()
        con.getresponse()
        con.close()

    lines = server_terminate()

    assert lines[-1] == 'Termination request received'


@pytest.mark.parametrize('num', range(1, 3))
def test_pipelined(num, connect, server_terminate):
    connections = []

    for _ in range(num):
        con = connect()
        connections.append(con)
        con.putrequest('GET', '/sleep/1')
        con.endheaders()

    lines = server_terminate()

    assert '{} connections busy, read-end closed'.format(num) in lines
    assert not any(l.startswith('Forcefully killing') for l in lines)

    assert all(c.getresponse().status == 200 for c in connections)


@pytest.mark.parametrize('num', range(1, 3))
def test_pipelined_timeout(num, connect, server_terminate):
    connections = []

    for _ in range(num):
        con = connect()
        connections.append(con)
        con.putrequest('GET', '/sleep/10')
        con.endheaders()

    lines = server_terminate()

    assert '{} connections busy, read-end closed'.format(num) in lines
    assert 'Forcefully killing {} connections'.format(num) in lines

    assert all(c.getresponse().status == 503 for c in connections)


def test_refuse(connect, server):
    con = connect()
    con.putrequest('GET', '/sleep/10')
    con.endheaders()

    server.terminate()

    # give time for the signal to propagate
    time.sleep(1)

    with pytest.raises(ConnectionRefusedError):
        con = connect()

    assert server.wait() == 0

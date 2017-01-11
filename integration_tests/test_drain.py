import pytest
import psutil
import subprocess
import sys
import time

import client


@pytest.fixture(scope='function')
def server():
    server = subprocess.Popen([
        sys.executable, 'integration_tests/drain.py',
        ], stdout=subprocess.PIPE)
    proc = psutil.Process(server.pid)

    # wait until the server socket is open
    while 1:
        if proc.connections():
            break
        time.sleep(.001)

    server.proc = proc
    return server


@pytest.fixture(scope='function')
def server_terminate(server):
    def terminate():
        server.terminate()
        assert server.wait() == 0

        stdout = server.communicate()[0]

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

    assert lines[-1] == 'Draining connections...'

def test_open_connections(connect, server_terminate):
    connect()
    print('maybe_connect')
    lines = server_terminate()

    assert lines[-1] == '1 idle connections closed immediately'

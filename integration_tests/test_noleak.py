import subprocess
import sys

import psutil
import pytest
import time
import os

import client

@pytest.fixture(scope='module')
def build_with_track():
    os.putenv('PYTHONPATH', '.test/noleak')

    subprocess.check_call([
        sys.executable, 'build.py', '--coverage', '--dest', '.test/noleak',
        '--extra-compile=-DPROTOCOL_TRACK_REFCNT=1'])

    yield

    os.putenv('PYTHONPATH', '.test')




@pytest.fixture(scope='function')
def server(build_with_track, request):
    arg = request.node.get_marker('arg').args[0]

    server = subprocess.Popen([
        sys.executable, 'integration_tests/noleak.py', arg])
    proc = psutil.Process(server.pid)

    # wait until the server socket is open
    while 1:
        if proc.connections():
            break
        time.sleep(.001)

    yield server

    server.terminate()
    server.wait()
    assert server.returncode == 0


@pytest.fixture(scope='function')
def connection(server):
    conn = client.Connection('localhost:8080')
    yield conn
    conn.close()


@pytest.mark.arg('method')
def test_method(connection):
    methods = ['GET', 'POST', 'PATCH', 'DELETE', 'PUT']

    for method in methods:
        connection.putrequest(method, '/noleak/1/2')
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('path')
def test_path(connection):
    paths = ['/noleak/1/2', '/noleak/3/4', '/noleak/5/4', '/noleak/6/7']

    for path in paths:
        connection.putrequest('GET', path)
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('match_dict')
def test_match_dict(connection):
    paths = ['/noleak/1/2', '/noleak/3/4', '/noleak/5/4', '/noleak/6/7']

    for path in paths:
        connection.putrequest('GET', path)
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('query_string')
def test_query_string(connection):
    query_strings = ['?', None, '?a', None, '?', None, '?b', None, '?']

    for query_string in query_strings:
        connection.putrequest('GET', '/noleak/1/2', query_string)
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('headers')
def test_headers(connection):
    header_list = [{}, {"X-a": "b"}, {}, {"X-b": "c"}, {}, {"X-c": "d"}]

    for headers in header_list:
        connection.putrequest('GET', '/noleak/1/2')
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('body')
def test_body(connection):
    bodies = [None, b'a', None, b'b', None, b'c', None, b'd', None, b'e']

    for body in bodies:
        connection.putrequest('GET', '/noleak/1/2')
        if body:
            connection.putheader('Content-Length', str(len(body)))
        connection.endheaders(body)

        response = connection.getresponse()
        assert response.status == 200


@pytest.mark.arg('keep_alive')
def test_keep_alive(request):
    keep_alives = [True, False, True, True, False, False, True, False]

    still_open = False

    for keep_alive in keep_alives:
        if not still_open:
            connection_gen = connection(request.getfixturevalue('server'))
            conn = next(connection_gen)
        still_open = keep_alive
        conn.putrequest('GET', '/noleak/1/2')
        if not keep_alive:
            conn.putheader('Connection', 'close')
        conn.endheaders()

        response = conn.getresponse()
        assert response.status == 200


@pytest.mark.arg('route')
def test_route(connection):
    for _ in range(7):
        connection.putrequest('GET', '/noleak/1/2')
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200

import pytest
from hypothesis import given, strategies as st, settings, Verbosity
import subprocess
import psutil
import sys
import time
from functools import partial

import client


@pytest.fixture(autouse=True, scope='module')
def server():
    server = subprocess.Popen([sys.executable, 'integration_tests/dump.py'])
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


@pytest.fixture()
def connect(request):
    return partial(client.Connection, 'localhost:8080')


full_request_line = 'GET /asd?qwe HTTP/1.1'
def make_truncated_request_line(cut):
    return full_request_line[:-cut]


st_request_cut = st.integers(min_value=1, max_value=len(full_request_line) - 1)
@given(request_line=st.builds(make_truncated_request_line, st_request_cut))
@settings(verbosity=Verbosity.verbose)
def test_truncated_request_line(connect, request_line):
    connection = connect()
    connection.putline(request_line)

    response = connection.getresponse()
    assert response.status == 400
    assert response.body.decode('utf-8') == 'malformed_headers'


full_header = 'X-Header: asd'
def make_truncated_header(cut):
    return full_header[:-cut]


st_header_cut = st.integers(min_value=5, max_value=len(full_header) - 1)
@given(header_line=st.builds(make_truncated_header, st_header_cut))
@settings(verbosity=Verbosity.verbose)
def test_truncated_header(connect, header_line):
    connection = connect()
    connection.putline(full_request_line)
    connection.putline(header_line)
    connection.putline()

    response = connection.getresponse()
    assert response.status == 400
    assert response.body.decode('utf-8') == 'malformed_headers'

import pytest
from hypothesis import given, strategies as st, settings, Verbosity
import subprocess
import psutil
import sys
import time
import queue
import threading
from functools import partial

import client
import integration_tests.common


pytestmark = pytest.mark.needs_build


@pytest.fixture(autouse=True, scope='module')
def server():
    server = integration_tests.common.start_server(
        ['-u', 'integration_tests/dump.py'],
        stdout=subprocess.PIPE, path='.test')

    yield server

    server.terminate()
    server.wait() == 0


@pytest.fixture
def line_getter(server):
    q = queue.Queue()

    def enqueue_output():
        q.put(server.stdout.readline().strip().decode('utf-8'))

    class LineGetter:
        def start(self):
            self.thread = threading.Thread(target=enqueue_output)
            self.thread.start()

        def wait(self):
            self.thread.join()
            return q.get()

    return LineGetter()


@pytest.fixture()
def connect(request):
    return partial(client.Connection, 'localhost:8080')


full_request_line = 'GET /asd?qwe HTTP/1.1'
def make_truncated_request_line(cut):
    return full_request_line[:-cut]


st_request_cut = st.integers(min_value=1, max_value=len(full_request_line) - 1)
st_request_line = st.builds(make_truncated_request_line, st_request_cut)
@given(request_line=st_request_line)
@settings(verbosity=Verbosity.verbose, max_examples=20)
def test_truncated_request_line(line_getter, connect, request_line):
    connection = connect()
    line_getter.start()

    connection.putline(request_line)

    assert line_getter.wait() == 'malformed_headers'

    response = connection.getresponse()
    assert response.status == 400
    assert response.text == 'malformed_headers'



@given(request_line=st_request_line)
@settings(verbosity=Verbosity.verbose, max_examples=20)
def test_truncated_request_line_disconnect(line_getter, connect, request_line):
    connection = connect()
    line_getter.start()

    connection.putclose(request_line)

    assert line_getter.wait() == 'incomplete_headers'


full_header = 'X-Header: asd'
def make_truncated_header(cut):
    return full_header[:-cut]


st_header_cut = st.integers(min_value=5, max_value=len(full_header) - 1)
st_header_line = st.builds(make_truncated_header, st_header_cut)
@given(header_line=st_header_line)
@settings(verbosity=Verbosity.verbose, max_examples=20)
def test_truncated_header(line_getter, connect, header_line):
    connection = connect()
    line_getter.start()
    connection.putline(full_request_line)
    connection.putline(header_line)
    connection.putline()

    assert line_getter.wait() == 'malformed_headers'

    response = connection.getresponse()
    assert response.status == 400
    assert response.text == 'malformed_headers'


@given(header_line=st_header_line)
@settings(verbosity=Verbosity.verbose, max_examples=20)
def test_truncated_header_disconnect(line_getter, connect, header_line):
    connection = connect()
    line_getter.start()
    connection.putline(full_request_line)
    connection.putclose(header_line)

    assert line_getter.wait() == 'incomplete_headers'


@pytest.mark.parametrize('value', [
    '',
    '+5',
    '-5',
    '0x12',
    '12a'
])
def test_invalid_content_length(line_getter, connect, value):
    connection = connect()
    line_getter.start()
    connection.putline(full_request_line)
    connection.putheader('Content-Length', value)
    connection.putline()

    assert line_getter.wait() == 'invalid_headers'

    response = connection.getresponse()
    assert response.status == 400
    assert response.text == 'invalid_headers'

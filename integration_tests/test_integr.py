import pytest
import subprocess
import sys
import os
import urllib3.connection
import client
import socket
import psutil
import time
import json
import urllib.parse
import string
import re
import ctypes.util
import base64
from functools import partial

from hypothesis import given, strategies as st, settings, Verbosity, HealthCheck

import integration_tests.common

@pytest.fixture(autouse=True, scope='module')
def server():
    server = integration_tests.common.start_server('integration_tests/dump.py')

    proc = psutil.Process(server.pid)

    collector = subprocess.Popen([
        sys.executable, 'integration_tests/collector.py', str(server.pid)])
    c_proc = psutil.Process(collector.pid)

    assert server.poll() is None
    assert collector.poll() is None

    # wait until the server socket is open
    try:
        while 1:
            if proc.connections():
                break
        time.sleep(.001)
    except psutil.AccessDenied:
        time.sleep(.2)

    assert server.poll() is None
    assert collector.poll() is None

    # wait until the collector socket is open
    try:
        while 1:
            if c_proc.connections():
                break
            time.sleep(.001)
    except psutil.AccessDenied:
        time.sleep(.2)

    assert server.poll() is None
    assert collector.poll() is None

    yield server

    server.terminate()
    server.wait()
    assert server.returncode == 0

    collector.wait()
    assert collector.returncode == 0


@pytest.fixture(scope='module')
def mark(server):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 8081))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(data):
        if data.startswith('test-'):
            data = data[5:]
        data += '\n'
        sock.sendall(data.encode('utf-8'))

    yield send

    sock.close()


@pytest.fixture(autouse=True)
def marker(request, mark):
    mark(request.node.name)


@pytest.fixture(params=['example', 'test'])
def connect(request):
    if request.param == 'example':
        yield partial(urllib3.connection.HTTPConnection, 'localhost:8080')
    elif request.param == 'test':
        connection = urllib3.connection.HTTPConnection('localhost:8080')
        close = connection.close
        connection.close = lambda: None
        yield lambda: connection
        close()


@pytest.fixture(params=['', '/async'], ids=['sync', 'async'])
def prefix(request):
    return request.param


method_alphabet = string.digits + string.ascii_letters + string.punctuation
st_method = st.text(method_alphabet, min_size=1)
@given(method=st_method)
@settings(verbosity=Verbosity.verbose)
def test_method(prefix, connect, method):
    connection = connect()
    connection.request(method, prefix + '/dump/1/2')
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['method'] == method

    connection.close()


st_route_prefix = st.sampled_from(['/dump/', '/dump1/', '/dump2/'])
@given(route_prefix=st_route_prefix)
@settings(verbosity=Verbosity.verbose)
def test_route(prefix, connect, route_prefix):
    connection = connect()
    connection.request('GET', prefix + route_prefix + '1/2')
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['route'].startswith(prefix + route_prefix)

    connection.close()


param_alphabet = st.characters(blacklist_characters='/?') \
    .filter(lambda x: not any(0xD800 <= ord(c) <= 0xDFFF for c in x))
st_param = st.text(param_alphabet, min_size=1)
@given(param1=st_param, param2=st_param)
@settings(verbosity=Verbosity.verbose)
def test_match_dict(prefix, connect, param1, param2):
    connection = connect()
    connection.request('GET', urllib.parse.quote(prefix + '/dump/{}/{}'.format(param1, param2)))
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['match_dict'] == {'p1': param1, 'p2': param2}

    connection.close()


st_query_string = st.one_of(st.text(), st.none())
@given(query_string=st_query_string)
@settings(verbosity=Verbosity.verbose)
def test_query_string(prefix, connect, query_string):
    connection = connect()
    url = prefix + '/dump/1/2'
    if query_string is not None:
        url += '?' + urllib.parse.quote(query_string)
    connection.request('GET', url)
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['query_string'] == query_string

    connection.close()


name_alphabet = string.digits + string.ascii_letters + '!#$%&\'*+-.^_`|~'
names = st.text(name_alphabet, min_size=1).map(lambda x: 'X-' + x)
value_alphabet = ''.join(chr(x) for x in range(ord(' '), 256) if x != 127)
is_illegal_value = re.compile(r'\n(?![ \t])|\r(?![ \t\n])').search
values = st.text(value_alphabet, min_size=1) \
    .filter(lambda x: not is_illegal_value(x)).map(lambda x: x.strip())
st_headers = st.lists(st.tuples(names, values), max_size=48)
@given(headers=st_headers)
@settings(
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.too_slow]
)
def test_headers(prefix, connect, headers):
    connection = connect()
    connection.putrequest(
        'GET', prefix + '/dump/1/2', skip_host=True, skip_accept_encoding=True)
    for name, value in headers:
        connection.putheader(name, value)
    connection.endheaders()

    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    headers = {k.title(): v for k, v in headers}
    assert json_body['headers'] == headers

    connection.close()


st_errors = st.sampled_from(['not-found', 'forced-1', 'forced-2'])
@given(error=st_errors)
@settings(
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.too_slow]
)
def test_error(prefix, connect, error):
    connection = connect()
    connection.putrequest(
        'GET', prefix + '/not-found' if error == 'not-found' else '/dump/1/2')
    if error != 'not-found':
        connection.putheader('Force-Raise', error)
    connection.endheaders()

    response = connection.getresponse()
    assert response.status == 500
    json_body = json.loads(response.read().decode('utf-8'))
    assert json_body['exception']['type'] == \
        'RouteNotFoundException' if error == 'not-found' else 'ForcedException'
    assert json_body['exception']['args'] == \
        '' if error == 'not-found' else error


st_body = st.one_of(st.binary(), st.none())
@given(body=st_body)
@settings(verbosity=Verbosity.verbose)
@pytest.mark.parametrize(
    'size_k', [0, 1, 2, 4, 8], ids=['small', '1k', '2k', '4k', '8k'])
def test_body(prefix, connect, size_k, body):
    if size_k and body:
        body = body * ((size_k * 1024) // len(body) + 1)

    connection = connect()
    connection.putrequest('GET', prefix + '/dump/1/2')
    if body is not None:
        connection.putheader('Content-Length', len(body))
    connection.endheaders(body)
    response = connection.getresponse()

    assert response.status == 200
    json_body = json.loads(response.read().decode('utf-8'))

    if body is not None:
        assert base64.b64decode(json_body['body']) == body
    else:
        assert json_body['body'] == body

    connection.close()


@given(body=st.lists(st.binary(min_size=24)))
@settings(verbosity=Verbosity.verbose)
@pytest.mark.parametrize(
    'size_k', [0, 1, 2, 4, 8], ids=['small', '1k', '2k', '4k', '8k'])
def test_chunked(prefix, connect, size_k, body):
    length = sum(len(b) for b in body)
    if size_k and length:
        body = body * ((size_k * 1024) // length + 1)

    connection = connect()
    connection.request_chunked('POST', prefix + '/dump/1/2', body=body)
    response = connection.getresponse()
    assert response.status == 200
    json_body = json.loads(response.read().decode('utf-8'))

    assert base64.b64decode(json_body['body']) == b''.join(body)

    connection.close()


st_errors = st.sampled_from([None, None, None, 'not-found', 'forced-1'])
@given(
    method=st_method,
    error=st_errors,
    route_prefix=st_route_prefix,
    param1=st_param, param2=st_param,
    query_string=st_query_string,
    headers=st_headers,
    body=st_body
)
@settings(
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.too_slow]
)
@pytest.mark.parametrize(
    'size_k', [0, 1, 2, 4, 8], ids=['small', '1k', '2k', '4k', '8k'])
def test_all(prefix, connect, size_k, method, error, route_prefix,
             param1, param2, query_string, headers, body):
    connection = connect()
    if size_k and body:
        body = body * ((size_k * 1024) // len(body) + 1)
    url = urllib.parse.quote(
        prefix + ('/not-found' if error == 'not-found' else '')
        + route_prefix + '{}/{}'.format(param1, param2))
    if query_string is not None:
        url += '?' + urllib.parse.quote(query_string)
    connection.putrequest(
        method, url, skip_host=True, skip_accept_encoding=True)
    for name, value in headers:
        connection.putheader(name, value)
    if body is not None:
        headers.append(('Content-Length', str(len(body))))
        connection.putheader('Content-Length', len(body))
    if error == 'forced-1':
        headers.append(('Force-Raise', 'forced-1'))
        connection.putheader('Force-Raise', 'forced-1')
    connection.endheaders(body)
    response = connection.getresponse()

    assert response.status == 500 if error else 200
    json_body = json.loads(response.read().decode('utf-8'))
    assert json_body['method'] == method
    if error != 'not-found':
        assert json_body['route'].startswith(prefix + route_prefix)
    else:
        assert json_body['route'] is None
    assert json_body['match_dict'] == \
        {} if error == 'not-found' else {'p1': param1, 'p2': param2}
    assert json_body['query_string'] == query_string
    headers = {k.title(): v for k, v in headers}
    assert json_body['headers'] == headers
    if body is not None:
        assert base64.b64decode(json_body['body']) == body
    else:
        assert json_body['body'] is None
    if error:
        assert json_body['exception']['type'] == \
            'RouteNotFoundException' if error == 'not-found' else 'ForcedException'
        assert json_body['exception']['args'] == \
            '' if error == 'not-found' else error
    else:
        assert 'exception' not in json_body

    connection.close()


st_request = st.fixed_dictionaries({
    'method': st_method,
    'error': st_errors,
    'route_prefix': st_route_prefix,
    'param1': st_param,
    'param2': st_param,
    'query_string': st_query_string,
    'headers': st_headers,
    'body': st_body
})
st_requests = st.lists(st_request, min_size=2)
@given(requests=st_requests)
@settings(
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.too_slow])
def test_pipeline(requests):
    connection = client.Connection('localhost:8080')

    for request in requests:
        connection.putrequest(
            request['method'], request['route_prefix'] +
             ('/not-found' if request['error'] == 'not-found' else '') +
            '{param1}/{param2}'.format_map(request),
            request['query_string'])
        for name, value in request['headers']:
            connection.putheader(name, value)
        if request['body'] is not None:
            body_len = str(len(request['body']))
            request['headers'].append(('Content-Length', body_len))
            connection.putheader('Content-Length', body_len)
        if request['error'] == 'forced-1':
            request['headers'].append(('Force-Raise', 'forced-1'))
            connection.putheader('Force-Raise', 'forced-1')
        connection.endheaders(request['body'])

    for request in requests:
        response = connection.getresponse()
        assert response.status == 500 if request['error'] else 200
        json_body = response.json
        assert json_body['method'] == request['method']
        if request['error'] != 'not-found':
            assert json_body['route'].startswith(request['route_prefix'])
        else:
            assert json_body['route'] is None
        assert json_body['match_dict'] == \
            {} if request['error'] == 'not-found' else \
            {'p1': request['param1'], 'p2': request['param2']}
        assert json_body['query_string'] == request['query_string']
        assert json_body['headers'] == {k.title(): v for k, v in request['headers']}
        if request['body'] is not None:
            assert base64.b64decode(json_body['body']) == request['body']
        else:
            assert json_body['body'] is None
        if request['error']:
            assert json_body['exception']['type'] == \
                'RouteNotFoundException' if request['error'] == 'not-found' else 'ForcedException'
            assert json_body['exception']['args'] == \
                '' if request['error'] == 'not-found' else request['error']
        else:
            assert 'exception' not in json_body


    connection.close()


def format_sleep_qs(val):
    return 'sleep=' + str(val / 100)
st_sleep = st.builds(format_sleep_qs, st.integers(min_value=0, max_value=10))
st_prefix = st.sampled_from(['/dump', '/async/dump'])
st_async_request = st.fixed_dictionaries({
    'query_string': st_sleep,
    'prefix': st_prefix,
    'error': st_errors
})
st_async_requests = st.lists(st_async_request, min_size=2, max_size=5) \
    .filter(lambda rs: any(r['prefix'].startswith('/async') for r in rs))
@given(requests=st_async_requests)
@settings(verbosity=Verbosity.verbose)
def test_async_pipeline(requests):
    connection = client.Connection('localhost:8080')

    for request in requests:
        connection.putrequest(
            'GET', request['prefix'] +
            ('/not-found' if request['error'] == 'not-found' else '') +
            '/1/2', request['query_string'])
        if request['error'] == 'forced-1':
            connection.putheader('Force-Raise', 'forced-1')

        connection.endheaders()

    for request in requests:
        response = connection.getresponse()
        assert response.status == 500 if request['error'] else 200
        json_body = response.json
        assert json_body['query_string'] == request['query_string']

    connection.close()

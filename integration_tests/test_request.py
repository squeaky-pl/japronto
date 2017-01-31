import pytest
import json
import base64
from functools import partial

from hypothesis import given, settings, Verbosity, HealthCheck

import integration_tests.common
from integration_tests import strategies as st
from misc import client


pytestmark = pytest.mark.needs_build(coverage=True)


@pytest.fixture(autouse=True, scope='module')
def server():
    server = integration_tests.common.start_server(
        'integration_tests/dump.py', path='.test')

    yield server

    server.terminate()
    server.wait() == 0


@pytest.fixture(params=['example', 'test'])
def connect(request):
    if request.param == 'example':
        yield partial(client.Connection, 'localhost:8080')
    elif request.param == 'test':
        connection = client.Connection('localhost:8080')
        close = connection.close
        connection.close = lambda: None
        yield lambda: connection
        close()


@pytest.fixture(params=['', '/async'], ids=['sync', 'async'])
def prefix(request):
    return request.param


@given(method=st.method)
@settings(verbosity=Verbosity.verbose)
def test_method(prefix, connect, method):
    connection = connect()
    connection.request(method, prefix + '/dump/1/2')
    response = connection.getresponse()
    json_body = json.loads(response.body)

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
    json_body = json.loads(response.body)

    assert response.status == 200
    assert json_body['route'].startswith(prefix + route_prefix)

    connection.close()


@given(param1=st.param, param2=st.param)
@settings(verbosity=Verbosity.verbose)
def test_match_dict(prefix, connect, param1, param2):
    connection = connect()
    connection.request('GET', prefix + '/dump/{}/{}'.format(param1, param2))
    response = connection.getresponse()
    json_body = json.loads(response.body)

    assert response.status == 200
    assert json_body['match_dict'] == {'p1': param1, 'p2': param2}

    connection.close()


@given(query_string=st.query_string)
@settings(verbosity=Verbosity.verbose)
def test_query_string(prefix, connect, query_string):
    connection = connect()
    connection.request('GET', prefix + '/dump/1/2', query_string)
    response = connection.getresponse()
    json_body = json.loads(response.body)

    assert response.status == 200
    assert json_body['query_string'] == query_string

    connection.close()


@given(headers=st.headers)
@settings(
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.too_slow]
)
def test_headers(prefix, connect, headers):
    connection = connect()
    connection.request('GET', prefix + '/dump/1/2', headers=headers)
    response = connection.getresponse()
    json_body = json.loads(response.body)

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
    json_body = json.loads(response.body)
    assert json_body['exception']['type'] == \
        'RouteNotFoundException' if error == 'not-found' else 'ForcedException'
    assert json_body['exception']['args'] == \
        '' if error == 'not-found' else error


@given(body=st.identity_body)
@settings(verbosity=Verbosity.verbose)
@pytest.mark.parametrize(
    'size_k', [0, 1, 2, 4, 8], ids=['small', '1k', '2k', '4k', '8k'])
def test_body(prefix, connect, size_k, body):
    if size_k and body:
        body = body * ((size_k * 1024) // len(body) + 1)

    connection = connect()
    connection.request('GET', prefix + '/dump/1/2', body=body)
    response = connection.getresponse()

    assert response.status == 200
    json_body = json.loads(response.body)

    if body is not None:
        assert base64.b64decode(json_body['body']) == body
    else:
        assert json_body['body'] == body

    connection.close()


@given(body=st.chunked_body)
@settings(verbosity=Verbosity.verbose)
@pytest.mark.parametrize(
    'size_k', [0, 1, 2, 4, 8], ids=['small', '1k', '2k', '4k', '8k'])
def test_chunked(prefix, connect, size_k, body):
    length = sum(len(b) for b in body)
    if size_k and length:
        body = body * ((size_k * 1024) // length + 1)

    connection = connect()
    connection.request('POST', prefix + '/dump/1/2', body=body)
    response = connection.getresponse()
    assert response.status == 200
    json_body = json.loads(response.body)

    assert base64.b64decode(json_body['body']) == b''.join(body)

    connection.close()


st_errors = st.sampled_from([None, None, None, 'not-found', 'forced-1'])


@given(
    method=st.method,
    error=st_errors,
    route_prefix=st_route_prefix,
    param1=st.param, param2=st.param,
    query_string=st.query_string,
    headers=st.headers,
    body=st.identity_body
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
    url = prefix + ('/not-found' if error == 'not-found' else '') \
        + route_prefix + '{}/{}'.format(param1, param2)
    connection.putrequest(method, url, query_string)
    for name, value in headers:
        connection.putheader(name, value)
    if body is not None:
        headers.append(('Content-Length', str(len(body))))
        connection.putheader('Content-Length', str(len(body)))
    if error == 'forced-1':
        headers.append(('Force-Raise', 'forced-1'))
        connection.putheader('Force-Raise', 'forced-1')
    connection.endheaders(body)
    response = connection.getresponse()

    assert response.status == 500 if error else 200
    json_body = json.loads(response.body)
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
            'RouteNotFoundException' if error == 'not-found' \
            else 'ForcedException'
        assert json_body['exception']['args'] == \
            '' if error == 'not-found' else error
    else:
        assert 'exception' not in json_body

    connection.close()


st_request = st.fixed_dictionaries({
    'method': st.method,
    'error': st_errors,
    'route_prefix': st_route_prefix,
    'param1': st.param,
    'param2': st.param,
    'query_string': st.query_string,
    'headers': st.headers,
    'body': st.identity_body
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
        assert json_body['headers'] == \
            {k.title(): v for k, v in request['headers']}
        if request['body'] is not None:
            assert base64.b64decode(json_body['body']) == request['body']
        else:
            assert json_body['body'] is None
        if request['error']:
            assert json_body['exception']['type'] == \
                'RouteNotFoundException' if request['error'] == 'not-found' \
                else 'ForcedException'
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

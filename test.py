from collections import namedtuple
from functools import partial
import types
import math
from unittest.mock import Mock

import pytest

import impl_cffi
from cases import base, parametrize_cases

testcase_fields = 'data,method,path,version,headers,body'

HttpTestCase = namedtuple('HTTPTestCase', testcase_fields)
ErrorTestCase = namedtuple('ErrorTestCase', 'data,error')

malformed_headers1 = ErrorTestCase(b"GET / HTTP 1.0", "malformed_headers")
malformed_headers2 = ErrorTestCase(b"GET / HTTP/2", "malformed_headers")
incomplete_headers = ErrorTestCase(b"GET / HTTP/1.0\r\nH", "incomplete_headers")

incomplete_body = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 5\r\n\r\nI", "incomplete_body")
extra_body = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 2\r\n\r\nehlollypapa", "incomplete_headers")
extra_body2 = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\nGET /", "incomplete_headers")


chunked_incomplete = ErrorTestCase(
    b"POST / HTTP/1.1\r\n\r\n10\r\nasd", "incomplete_body")
chunked_malformed1 = ErrorTestCase(
    b"POST / HTTP/1.1\r\n\r\n1x\r\nhello", "malformed_body")
# phr doesnt choke on this one
chunked_malformed2 = ErrorTestCase(
    b"POST / HTTP/1.1\r\n\r\n5\rhello\r\n0\r\n\r\n", "malformed_body")
chunked_extra = ErrorTestCase(
    b"POST / HTTP/1.1\r\n\r\n5\r\nhello\r\n0\r\n\r\nGET /", "incomplete_headers")


def make_parts(value, get_size, dir=1):
    parts = []

    left = bytearray(value)
    while left:
        if isinstance(get_size, types.GeneratorType):
            size = next(get_size)
        else:
            size = get_size

        if dir == 1:
            parts.append(bytes(left[:size]))
            left = left[size:]
        else:
            parts.append(bytes(left[-size:]))
            left = left[:-size]

    return parts if dir == 1 else list(reversed(parts))


def one_part(value):
    return [value]


def geometric_series():
    s = 2
    while 1:
        yield s
        s *= 2


def fancy_series():
    x = 0
    while 1:
        yield int(2 + abs(math.sin(x / 5)) * 64)
        x += 1


def make_part_functions():
    return [
        one_part,
        partial(make_parts, get_size=15),
        partial(make_parts, get_size=geometric_series()),
        partial(make_parts, get_size=geometric_series(), dir=-1),
        partial(make_parts, get_size=fancy_series())
    ]


@pytest.mark.parametrize('data,get_size,dir,parts',
[
    (b'abcde', 2, 1, [b'ab', b'cd', b'e']),
    (b'abcde', 2, -1, [b'a', b'bc', b'de']),
    (b'aaBBBBccccCCCCd', geometric_series(), 1,
     [b'aa', b'BBBB', b'ccccCCCC', b'd']),
    (b'dCCCCccccBBBBaa', geometric_series(), -1,
     [b'd', b'CCCCcccc', b'BBBB', b'aa'])
])
def test_make_parts(data, get_size, dir, parts):
    assert make_parts(data, get_size, dir) == parts


@pytest.fixture
def parser():
    on_headers = Mock()
    on_error = Mock()
    on_body = Mock()
    parser = impl_cffi.HttpRequestParser(on_headers, on_error, on_body)

    return parser


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '10long', '10short', '10long+10short', '10short+10long')
def test_http10(parser, do_parts, cases):
    for i, case in enumerate(cases, 1):
        parts = do_parts(case.data)

        for part in parts:
            parser.feed(part)
        parser.feed_disconnect()

        assert parser.on_headers.call_count == i
        assert not parser.on_error.called
        assert parser.on_body.call_count == i

        request = parser.on_headers.call_args[0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers
        assert request.body == case.body


@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize('data,error', [
    malformed_headers2, malformed_headers1, incomplete_headers])
def test_http10_malformed(parser, do_parts, data, error):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert not parser.on_headers.called
    assert parser.on_error.call_args[0][0] == error
    assert not parser.on_body.called


def test_empty(parser):
    parser.feed_disconnect()
    parser.feed(b'')
    parser.feed(b'')
    parser.feed_disconnect()
    parser.feed_disconnect()
    parser.feed(b'')

    assert not parser.on_headers.called
    assert not parser.on_error.called
    assert not parser.on_body.called


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '11clkeep', '11clzero', '11clclose',
    '11clkeep+11clclose', '11clkeep+11clkeep',
    '11clclose+11clkeep', '11clclose+11clclose',
    '11clclose+11clclose+11clkeep',
    '11clkeep+11clclose+11clkeep',
    '11clclose+11clzero+11clkeep',
    '11clzero+11clclose+11clzero',
    '11clzero+11clzero'
)
def test_http11_contentlength(parser, do_parts, cases):
    data = b''.join(c.data for c in cases)
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_headers.call_count == len(cases)
    assert not parser.on_error.called
    assert parser.on_body.call_count == sum(1 for c in cases if c.body)

    for i, case in enumerate(cases):
        request = parser.on_headers.call_args_list[i][0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers
        assert request.body == case.body


@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize('data,error', [incomplete_body, extra_body, extra_body2])
def test_http11_malformed(parser, do_parts, data, error):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_error.call_args[0][0] == error


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '11chunked1', '11chunked2', '11chunked3',
    '11chunked1+11chunked1',
    '11chunked1+11chunked2',
    '11chunked2+11chunked1',
    '11chunked2+11chunked3',
    '11chunked1+11chunked2+11chunked3',
    '11chunked3+11chunked2+11chunked1',
    '11chunked3+11chunked3+11chunked3'
)
def test_http11_chunked(parser, do_parts, cases):
    data = b''.join(c.data for c in cases)
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_headers.call_count == len(cases)
    assert not parser.on_error.called
    assert parser.on_body.call_count == sum(1 for c in cases if c.body)

    for i, case in enumerate(cases):
        request = parser.on_headers.call_args_list[i][0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers
        assert request.body == (case.body or None)


@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize('data,error',
[
    chunked_incomplete,
    chunked_malformed1,
#    chunked_malformed2, phr doesnt choke
    chunked_extra
])
def test_http11_chunked_malformed(parser, do_parts, data, error):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_error.call_args[0][0] == error

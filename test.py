from collections import namedtuple
from functools import partial
import types
import math
from unittest.mock import Mock

import pytest

import impl_cffi
from cases import base, parametrize_cases


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
    parser = impl_cffi.HttpRequestParser(on_headers, on_body, on_error)

    return parser, on_headers, on_error, on_body


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '10long', '10short', '10long+10short', '10short+10long',

    '10malformed_headers1', '10malformed_headers2', '10incomplete_headers',
    '10long+10malformed_headers2', '10long+10incomplete_headers',
    '10short+10malformed_headers1', '10short+10malformed_headers2')
def test_http10(parser, do_parts, cases):
    parser, on_headers, on_error, on_body = parser
    for i, case in enumerate(cases, 1):
        parts = do_parts(case.data)

        for part in parts:
            parser.feed(part)
        parser.feed_disconnect()

        header_errors = 1 if case.error and 'headers' in case.error else 0
        body_errors = 1 if case.error and 'body' in case.error else 0

        assert on_headers.call_count == i - header_errors
        assert on_error.call_count == header_errors + body_errors
        assert on_body.call_count == i - header_errors - body_errors

        if on_error.called:
            assert on_error.call_args[0][0] == case.error

        if header_errors:
            continue

        request = on_headers.call_args[0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if body_errors:
            continue

        assert request.body == case.body


def test_empty(parser):
    parser, on_headers, on_error, on_body = parser

    parser.feed_disconnect()
    parser.feed(b'')
    parser.feed(b'')
    parser.feed_disconnect()
    parser.feed_disconnect()
    parser.feed(b'')

    assert not on_headers.called
    assert not on_error.called
    assert not on_body.called


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '11get', '11clget', '11clkeep', '11clzero', '11clclose',
    '11clkeep+11clclose', '11clkeep+11clkeep',
    '11clclose+11clkeep', '11clclose+11clclose',
    '11get+11clclose', '11clkeep+11get', '11clget+11get',
    '11clclose+11clclose+11clkeep',
    '11clkeep+11clclose+11clkeep',
    '11clclose+11clzero+11clkeep',
    '11clzero+11clclose+11clzero',
    '11clkeep+11get+11clzero',
    '11clzero+11clzero',
    '11get+11clget+11get',

    '11clincomplete_headers', '11clincomplete_body',
    '11clkeep+11clincomplete_headers', '11clkeep+11clincomplete_body',
    '11clzero+11clincomplete_headers', '11clzero+11clincomplete_body',
    '11clclose+11clkeep+11clincomplete_body',
    '11get+11clincomplete_body',
    '11clget+11clincomplete_headers'
)
def test_http11_contentlength(parser, do_parts, cases):
    parser, on_headers, on_error, on_body = parser

    data = b''.join(c.data for c in cases)
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    header_count = 0
    error_count = 0
    body_count = 0

    for i, case in enumerate(cases):
        if case.error and 'headers' in case.error:
            error_count += 1
            continue

        header_count += 1
        request = on_headers.call_args_list[i][0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error and 'body' in case.error:
            error_count += 1
            continue

        body_count += 1

        assert request.body == case.body

    assert on_headers.call_count == header_count
    assert on_error.call_count == error_count
    assert on_body.call_count == body_count


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '11chunked1', '11chunked2', '11chunked3', '11chunkedzero',
    '11chunked1+11chunked1',
    '11chunked1+11chunked2',
    '11chunked2+11chunked1',
    '11chunked2+11chunked3',
    '11chunked1+11chunked2+11chunked3',
    '11chunked3+11chunked2+11chunked1',
    '11chunked3+11chunked3+11chunked3',

    '11chunkedincomplete_body', '11chunkedmalformed_body',
    '11chunked1+11chunkedincomplete_body',
    '11chunked1+11chunkedmalformed_body',
    '11chunked2+11chunkedincomplete_body',
    '11chunked2+11chunkedmalformed_body',
    '11chunked2+11chunked2+11chunkedincomplete_body',
    '11chunked3+11chunked1+11chunkedmalformed_body'
)
def test_http11_chunked(parser, do_parts, cases):
    parser, on_headers, on_error, on_body = parser
    data = b''.join(c.data for c in cases)
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
        if on_error.called:
            break
    parser.feed_disconnect()

    header_count = 0
    error_count = 0
    body_count = 0

    for i, case in enumerate(cases):
        if case.error and 'headers' in case.error:
            error_count += 1
            continue

        header_count += 1
        request = on_headers.call_args_list[i][0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error and 'body' in case.error:
            error_count += 1
            continue

        body_count += 1

        assert request.body == case.body

    assert on_headers.call_count == header_count
    assert on_error.call_count == error_count
    assert on_body.call_count == body_count


@pytest.mark.parametrize('do_parts', make_part_functions())
@parametrize_cases(
    'base',
    '11chunked1+11clzero',
    '11clkeep+11chunked2',
    '11chunked2+11clclose',
    '11clzero+11chunked3',
    '11clclose+11chunked1+11chunked3',
    '11chunked3+11clkeep+11clclose',
    '11chunked3+11chunked3+11clclose'
)
def test_http11_mixed(parser, do_parts, cases):
    parser, on_headers, on_error, on_body = parser
    data = b''.join(c.data for c in cases)
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert on_headers.call_count == len(cases)
    assert not on_error.called
    assert on_body.call_count == len(cases)

    for i, case in enumerate(cases):
        request = on_headers.call_args_list[i][0][0]

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers
        assert request.body == case.body

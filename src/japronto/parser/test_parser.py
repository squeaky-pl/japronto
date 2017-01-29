from functools import partial
from itertools import zip_longest

import pytest

from cases import parametrize_cases
from parts import one_part, make_parts, geometric_series, fancy_series
from protocol.tracing import CTracingProtocol, CffiTracingProtocol
from parser import cffiparser, header_errors, body_errors
try:
    from parser import cparser
except ImportError:
    cparser = None


if cparser:
    def make_c(protocol_factory=CTracingProtocol):
        protocol = protocol_factory()
        parser = cparser.HttpRequestParser(
            protocol.on_headers, protocol.on_body, protocol.on_error)

        return parser, protocol


def make_cffi(protocol_factory=CffiTracingProtocol):
    protocol = protocol_factory()
    parser = cffiparser.HttpRequestParser(
        protocol.on_headers, protocol.on_body, protocol.on_error)

    return parser, protocol


@pytest.mark.parametrize('data,get_size,dir,parts', [
    (b'abcde', 2, 1, [b'ab', b'cd', b'e']),
    (b'abcde', 2, -1, [b'a', b'bc', b'de']),
    (b'aaBBBBccccCCCCd', geometric_series(), 1,
     [b'aa', b'BBBB', b'ccccCCCC', b'd']),
    (b'dCCCCccccBBBBaa', geometric_series(), -1,
     [b'd', b'CCCCcccc', b'BBBB', b'aa'])
])
def test_make_parts(data, get_size, dir, parts):
    assert make_parts(data, get_size, dir) == parts


def parametrize_make_parser():
    ids = []
    factories = []
    if 'make_c' in globals():
        factories.append(make_c)
        ids.append('c')

    factories.append(make_cffi)
    ids.append('cffi')

    return pytest.mark.parametrize('make_parser', factories, ids=ids)


def parametrize_do_parts():
    funcs = [
        one_part,
        partial(make_parts, get_size=15),
        partial(make_parts, get_size=geometric_series()),
        partial(make_parts, get_size=geometric_series(), dir=-1),
        partial(make_parts, get_size=fancy_series())
    ]

    ids = ['one', 'const', 'geom', 'invgeom', 'fancy']

    return pytest.mark.parametrize('do_parts', funcs, ids=ids)


_begin = object()
_end = object()


@parametrize_do_parts()
@parametrize_cases(
    'base',
    '10msg', '10msg!', '10get', '10get!', 'keep:10msg+10get',
    'keep:10get+10msg',

    '10malformed_headers1', '10malformed_headers2', '10incomplete_headers!',
    'keep:10msg+10malformed_headers2', 'keep:10msg+10incomplete_headers!',
    'keep:10get+10malformed_headers1', 'keep:10get+10malformed_headers2',

    '10msg!+10get!', '10get!+10msg!',
    '10msg!+keep:10get+keep:10msg+10get',
    '10msg+e excessive_data:10get', '10get+e excessive_data:10msg')
@parametrize_make_parser()
def test_http10(make_parser, do_parts, cases):
    parser, protocol = make_parser()

    def flush():
        nonlocal data
        if not data:
            return

        parts = do_parts(data)

        for part in parts:
            parser.feed(part)
            if protocol.error:
                break

        data = b''

    data = b''
    for case in cases:
        data += case.data

        if case.disconnect:
            flush()
            parser.feed_disconnect()
    flush()

    header_count = 0
    error_count = 0
    body_count = 0

    for case, request in zip_longest(cases, protocol.requests):
        if case.error:
            assert protocol.error == case.error

        if case.error in header_errors:
            error_count += 1
            break

        header_count += 1

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error in body_errors:
            error_count += 1
            break

        body_count += 1

        assert request.body == case.body

    assert protocol.on_headers_call_count == header_count
    assert protocol.on_error_call_count == error_count
    assert protocol.on_body_call_count == body_count


@parametrize_make_parser()
def test_empty(make_parser):
    parser, protocol = make_parser()

    parser.feed_disconnect()
    parser.feed(b'')
    parser.feed(b'')
    parser.feed_disconnect()
    parser.feed_disconnect()
    parser.feed(b'')

    assert not protocol.on_headers_call_count
    assert not protocol.on_error_call_count
    assert not protocol.on_body_call_count


@parametrize_do_parts()
@parametrize_cases(
    'base',
    '11get', '11getmsg', '11msg', '11msgzero', 'close:11get', 'close:11msg',
    '11get!', '11getmsg!', '11msg!', 'close:11msgzero!',
    '11msg+close:11msg', '11msg+11msg',
    'close:11msg!+11msg', 'close:11msg!+close:11msg',
    '11msg!+close:11msg', '11msg!+11msg',
    '11get+close:11msg', '11msg+11get', '11getmsg+11get',
    '11get+close:11msg!', '11msg!+11get', '11getmsg!+11get!',
    '11msg+11msg+close:11msg',
    '11msg+11msg+11msg',
    '11msg+11msgzero+11msg',
    '11msgzero+11msg+11msgzero',
    '11msg+11get+11msgzero',
    '11msgzero+11msgzero',
    '11get+11getmsg+11get',

    'close:11msg+e excessive_data:11msg',
    'close:11msg+e excessive_data:close:11msg',
    'close:11msg+e excessive_data:close:11msg+11msg',
    '11msg+close:11msgzero+e excessive_data:11get',

    '11clincomplete_headers!', '11clincomplete_body!',
    '11clinvalid1', '11clinvalid2', '11clinvalid3',
    '11clinvalid4', '11clinvalid5',
    '11msg+11clincomplete_headers!', 'close:11msg!+11clincomplete_body!',
    '11msgzero+11clincomplete_headers!', '11msgzero+11clincomplete_body!',
    'close:11msg!+11msg+11clincomplete_body!',
    '11get+11clincomplete_body!',
    '11getmsg+11clincomplete_headers!'
)
@parametrize_make_parser()
def test_http11(make_parser, do_parts, cases):
    parser, protocol = make_parser()

    def flush():
        nonlocal data
        if not data:
            return

        parts = do_parts(data)

        for part in parts:
            parser.feed(part)
            if protocol.error:
                break

        data = b''

    data = b''
    for case in cases:
        data += case.data

        if case.disconnect:
            flush()
            parser.feed_disconnect()
    flush()

    header_count = 0
    error_count = 0
    body_count = 0

    for case, request in zip_longest(cases, protocol.requests):
        if case.error:
            assert protocol.error == case.error

        if case.error in header_errors:
            error_count += 1
            break

        header_count += 1

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error in body_errors:
            error_count += 1
            break

        body_count += 1

        assert request.body == case.body

    assert protocol.on_headers_call_count == header_count
    assert protocol.on_error_call_count == error_count
    assert protocol.on_body_call_count == body_count


@parametrize_do_parts()
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

    '11chunkedincomplete_body!', '11chunkedmalformed_body',
    '11chunked1+11chunkedincomplete_body!',
    '11chunked1+11chunkedmalformed_body',
    '11chunked2+11chunkedincomplete_body!',
    '11chunked2+11chunkedmalformed_body',
    '11chunked2+11chunked2+11chunkedincomplete_body!',
    '11chunked3+11chunked1+11chunkedmalformed_body'
)
@parametrize_make_parser()
def test_http11_chunked(make_parser, do_parts, cases):
    parser, protocol = make_parser()

    def flush():
        nonlocal data
        if not data:
            return

        parts = do_parts(data)

        for part in parts:
            parser.feed(part)
            if protocol.error:
                break

        data = b''

    data = b''
    for case in cases:
        data += case.data

        if case.disconnect:
            flush()
            parser.feed_disconnect()
    flush()

    header_count = 0
    error_count = 0
    body_count = 0

    for case, request in zip_longest(cases, protocol.requests):
        if case.error:
            assert protocol.error == case.error

        if case.error in header_errors:
            error_count += 1
            break

        header_count += 1

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error in body_errors:
            error_count += 1
            break

        body_count += 1

        assert request.body == case.body

    assert protocol.on_headers_call_count == header_count
    assert protocol.on_error_call_count == error_count
    assert protocol.on_body_call_count == body_count


@parametrize_do_parts()
@parametrize_cases(
    'base',
    '11chunked1+11msgzero',
    '11msg+11chunked2',
    '11chunked2+close:11msg',
    '11msgzero+11chunked3',
    'close:11msg+e excessive_data:11chunked1+11chunked3',
    '11chunked3+11msg+close:11msg',
    '11chunked3+11chunked3+close:11msg'
)
@parametrize_make_parser()
def test_http11_mixed(make_parser, do_parts, cases):
    parser, protocol = make_parser()

    def flush():
        nonlocal data
        if not data:
            return

        parts = do_parts(data)

        for part in parts:
            parser.feed(part)
            if protocol.error:
                break

        data = b''

    data = b''
    for case in cases:
        data += case.data

        if case.disconnect:
            flush()
            parser.feed_disconnect()
    flush()

    header_count = 0
    error_count = 0
    body_count = 0

    for case, request in zip_longest(cases, protocol.requests):
        if case.error:
            assert protocol.error == case.error

        if case.error in header_errors:
            error_count += 1
            break

        header_count += 1

        assert request.method == case.method
        assert request.path == case.path
        assert request.version == case.version
        assert request.headers == case.headers

        if case.error in body_errors:
            error_count += 1
            break

        body_count += 1

        assert request.body == case.body

    assert protocol.on_headers_call_count == header_count
    assert protocol.on_error_call_count == error_count
    assert protocol.on_body_call_count == body_count

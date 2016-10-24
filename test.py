import pytest

from unittest.mock import Mock
from collections import namedtuple
from functools import partial
import inspect
import types
import math

import impl_cffi

testcase_fields = 'data,method,path,version,headers,body'

HttpTestCase = namedtuple('HTTPTestCase', testcase_fields)
ErrorTestCase = namedtuple('ErrorTestCase', 'data,error')

http10long = HttpTestCase(
b"""POST /wp-content/uploads/2010/03/hello-kitty-darth-vader-pink.jpg HTTP/1.0\r
HOST: www.kittyhell.com\r
User-Agent: Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; ja-JP-mac; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 Pathtraq/0.9\r
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r
Accept-Language: ja,en-us;q=0.7,en;q=0.3\r
Accept-Encoding: gzip,deflate\r
Accept-Charset: Shift_JIS,utf-8;q=0.7,*;q=0.7\r
Keep-Alive: 115\r
Cookie: wp_ozh_wsa_visits=2; wp_ozh_wsa_visit_lasttime=xxxxxxxxxx; __utma=xxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.x; __utmz=xxxxxxxxx.xxxxxxxxxx.x.x.utmccn=(referral)|utmcsr=reader.livedoor.com|utmcct=/reader/|utmcmd=referral\r
\r
Hello there""",
"POST",
"/wp-content/uploads/2010/03/hello-kitty-darth-vader-pink.jpg",
"1.0",
{
    "Host": "www.kittyhell.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; ja-JP-mac; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 Pathtraq/0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-us;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip,deflate",
    "Accept-Charset": "Shift_JIS,utf-8;q=0.7,*;q=0.7",
    "Keep-Alive": "115",
    "Cookie": "wp_ozh_wsa_visits=2; wp_ozh_wsa_visit_lasttime=xxxxxxxxxx; __utma=xxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.xxxxxxxxxx.x; __utmz=xxxxxxxxx.xxxxxxxxxx.x.x.utmccn=(referral)|utmcsr=reader.livedoor.com|utmcct=/reader/|utmcmd=referral"
},
b"Hello there"
)

http10short = HttpTestCase(
b"""POST / HTTP/1.0\r
Host: www.example.com\r
\r
Hi!""",
"POST",
"/",
"1.0",
{"Host": "www.example.com"},
b"Hi!"
)

malformed_headers1 = ErrorTestCase(b"GET / HTTP 1.0", "malformed_headers")
malformed_headers2 = ErrorTestCase(b"GET / HTTP/2", "malformed_headers")
incomplete_headers = ErrorTestCase(b"GET / HTTP/1.0\r\nH", "incomplete_headers")

http11_contentlength_keep = HttpTestCase(
b"""POST /login HTTP/1.1\r
Content-Length: 5\r
\r
Hello""",
"POST",
"/login",
"1.1",
{"Content-Length": "5"},
b"Hello"
)

http11_contentlength_zero = HttpTestCase(
b"""POST /zero HTTP/1.1\r
Content-Length: 0\r
\r
""",
"POST",
"/zero",
"1.1",
{"Content-Length": "0"},
b""
)

http11_contentlength_close = HttpTestCase(
b"""POST /logout HTTP/1.1\r
Content-Length: 3\r
Connection: close\r
\r
Bye""",
"POST",
"/logout",
"1.1",
{"Content-Length": "3", "Connection": "close"},
b"Bye"
)

incomplete_body = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 5\r\n\r\nI", "incomplete_body")
extra_body = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 2\r\n\r\nehlollypapa", "incomplete_headers")
extra_body2 = ErrorTestCase(
    b"POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\nGET /", "incomplete_headers")

http11_chunked1 = HttpTestCase(
b"""POST /chunked HTTP/1.1\r
\r
4\r
Wiki\r
5\r
pedia\r
E\r
 in\r
\r
chunks.\r
0\r
\r""",
"POST",
"/chunked",
"1.1",
{},
b"Wikipedia in\r\n\r\nchunks.")

http11_chunked2 = HttpTestCase(
b"""POST /chunked HTTP/1.1\r
\r
1\r
r\r
0\r
\r""",
"POST",
"/chunked",
"1.1",
{},
b'r')

http11_chunked3 = HttpTestCase(
b"""POST / HTTP/1.1\r
\r
000002\r
ab\r
0\r
\r""",
"POST",
"/",
"1.1",
{},
b'ab')


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
@pytest.mark.parametrize(testcase_fields, [http10long, http10short])
def test_http10_one_request(parser, do_parts, data, method, path, version, headers, body):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_headers.called
    assert not parser.on_error.called
    assert parser.on_body.called

    request = parser.on_headers.call_args[0][0]

    assert request.method == method
    assert request.path == path
    assert request.version == version
    assert request.headers == headers
    assert request.body == body


@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize('cases',
    [[http10long, http10short], [http10short, http10long]])
def test_http10_many_requests(parser, do_parts, cases):
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
@pytest.mark.parametrize(testcase_fields,
[
    http11_contentlength_keep,
    http11_contentlength_close,
    http11_contentlength_zero
])
def test_http11_contentlength_one_request(
        parser, do_parts,
        data, method, path, version, headers, body):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)

    assert parser.on_headers.called
    assert not parser.on_error.called
    assert parser.on_body.called == bool(body)

    request = parser.on_headers.call_args[0][0]

    assert request.method == method
    assert request.path == path
    assert request.version == version
    assert request.headers == headers
    assert request.body == (body or None)


@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize('cases',
[
    [http11_contentlength_keep, http11_contentlength_close],
    [http11_contentlength_keep, http11_contentlength_keep],
    [http11_contentlength_close, http11_contentlength_keep],
    [http11_contentlength_close, http11_contentlength_close],
    [http11_contentlength_close, http11_contentlength_close, http11_contentlength_keep],
    [http11_contentlength_keep, http11_contentlength_close, http11_contentlength_keep],
    [http11_contentlength_close, http11_contentlength_zero, http11_contentlength_keep],
    [http11_contentlength_zero, http11_contentlength_close, http11_contentlength_zero],
    [http11_contentlength_zero, http11_contentlength_zero]
])
def test_http11_contentlength_many_requests(parser, do_parts, cases):
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
@pytest.mark.parametrize('data,error', [incomplete_body, extra_body, extra_body2])
def test_http11_malformed(parser, do_parts, data, error):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)
    parser.feed_disconnect()

    assert parser.on_error.call_args[0][0] == error



@pytest.mark.parametrize('do_parts', make_part_functions())
@pytest.mark.parametrize(testcase_fields,
[
    http11_chunked1,
    http11_chunked2,
    http11_chunked3
])
def test_http11_contentlength_one_request(
        parser, do_parts,
        data, method, path, version, headers, body):
    parts = do_parts(data)

    for part in parts:
        parser.feed(part)

    assert parser.on_headers.called
    assert not parser.on_error.called
    assert parser.on_body.called

    request = parser.on_headers.call_args[0][0]

    assert request.method == method
    assert request.path == path
    assert request.version == version
    assert request.headers == headers
    assert request.body == body

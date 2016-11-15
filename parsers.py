from functools import partial

from libpicohttpparser import ffi
from request import HttpRequest


import impl_cffi
try:
    import impl_cext
except ImportError:
    impl_cext = None


class TestProtocol:
    def __init__(self, on_headers_adapter: callable,
                 on_body_adapter: callable):
        self.requests = []
        self.error = None

        self.on_headers_adapter = on_headers_adapter
        self.on_body_adapter = on_body_adapter

        self.on_headers_call_count = 0
        self.on_body_call_count = 0
        self.on_error_call_count = 0

    def on_headers(self, *args):
        self.request = self.on_headers_adapter(*args)

        self.requests.append(self.request)

        self.on_headers_call_count += 1

    def on_body(self, body):
        self.request.body = self.on_body_adapter(body)

        self.on_body_call_count += 1

    def on_error(self, error: str):
        self.error = error

        self.on_error_call_count += 1


def _request_from_cprotocol(method: memoryview, path: memoryview, version: int,
                            headers: memoryview):
    method = method.tobytes().decode('ascii')
    path = path.tobytes().decode('ascii')
    version = "1.0" if version == 0 else "1.1"
    headers_len = headers.nbytes // ffi.sizeof("struct phr_header")
    headers_cdata = ffi.from_buffer(headers)
    headers_cdata = ffi.cast(
        'struct phr_header[{}]'.format(headers_len), headers_cdata)

    headers = _extract_headers(headers_cdata)

    return HttpRequest(method, path, version, headers)


def _body_from_cprotocol(body: memoryview):
    return body.tobytes()


def _extract_headers(headers_cdata: "struct phr_header[]"):
    headers = {}
    for header in headers_cdata:
        name = ffi.string(header.name, header.name_len).decode('ascii').title()
        value = ffi.string(header.value, header.value_len).decode('latin1')
        headers[name] = value

    return headers


CTestProtocol = partial(
    TestProtocol, on_headers_adapter=_request_from_cprotocol,
    on_body_adapter=_body_from_cprotocol)


def silent_callback(*args):
    pass


def debug_callback(*args):
    print(args)
    if isinstance(args[0], impl_cffi.HttpRequest):
        print(args[0].body)


if impl_cext:
    def make_cext(cb_factory):
        on_headers = cb_factory()
        on_error = cb_factory()
        on_body = cb_factory()
        parser_cext = \
            impl_cext.HttpRequestParser(on_headers, on_body, on_error)

        return parser_cext, on_headers, on_error, on_body


def make_cffi(cb_factory):
    on_headers = cb_factory()
    on_error = cb_factory()
    on_body = cb_factory()
    parser_cffi = impl_cffi.HttpRequestParser(on_headers, on_body, on_error)

    return parser_cffi, on_headers, on_error, on_body

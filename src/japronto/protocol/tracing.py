from functools import partial

from parser.libpicohttpparser import ffi
from request import HttpRequest


class TracingProtocol:
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
    return None if body is None else body.tobytes()


def _request_from_cffiprotocol(method: "char[]", path: "char[]", version: int,
                               headers: "struct phr_header[]"):
    method = ffi.buffer(method)[:].decode('ascii')
    path = ffi.buffer(path)[:].decode('ascii')
    version = "1.0" if version == 0 else "1.1"

    headers = _extract_headers(headers)

    return HttpRequest(method, path, version, headers)


def _body_from_cffiprotocol(body: "char[]"):
    return None if body is None else ffi.buffer(body)[:]


def _extract_headers(headers_cdata: "struct phr_header[]"):
    headers = {}
    for header in headers_cdata:
        name = ffi.string(header.name, header.name_len).decode('ascii').title()
        value = ffi.string(header.value, header.value_len).decode('latin1')
        headers[name] = value

    return headers


CTracingProtocol = partial(
    TracingProtocol, on_headers_adapter=_request_from_cprotocol,
    on_body_adapter=_body_from_cprotocol)


CffiTracingProtocol = partial(
    TracingProtocol, on_headers_adapter=_request_from_cffiprotocol,
    on_body_adapter=_body_from_cffiprotocol)

from __future__ import print_function

from libpicohttpparser import ffi, lib


NO_SEMANTICS = ["GET", "HEAD", "DELETE"]


class HttpRequest(object):
    def __init__(self, method, path, version, headers):
        self.path = path
        self.method = method
        self.version = version
        self.headers = headers
        self.body = None

    def dump_headers(self):
        print('path', self.path)
        print('method', self.method)
        print('version', self.version)
        for n, v in self.headers.items():
            print(n, v)


class HttpRequestParser(object):
    def __init__(self, on_headers, on_error, on_body):
        self.on_headers = on_headers
        self.on_error = on_error
        self.on_body = on_body

        self.c_method = ffi.new('char **')
        self.method_len = ffi.new('size_t *')
        self.c_path = ffi.new('char **')
        self.path_len = ffi.new('size_t *')
        self.minor_version = ffi.new('int *')
        self.c_headers = ffi.new('struct phr_header[10]')
        self.num_headers = ffi.new('size_t *')
        self.chunked_offset = ffi.new('size_t*')

        self.buffer = bytearray()
        self._reset_state()

    def _reset_state(self):
        self.request = None
        self.state = 'headers'
        self.connection = None
        self.transfer = None
        self.content_length = None
        self.chunked_decoder = None
        self.chunked_offset[0] = 0

    def _parse_headers(self):
        self.num_headers[0] = 10

        # FIXME: More than 10 headers

        result = lib.phr_parse_request(
            ffi.from_buffer(self.buffer), len(self.buffer),
            self.c_method, self.method_len,
            self.c_path, self.path_len,
            self.minor_version, self.c_headers, self.num_headers, 0)

        if result == -2:
            return result
        elif result == -1:
            self.on_error('malformed_headers')
            self._reset_state()
            self.buffer = bytearray()

            return result
        else:
            self._reset_state()

        method = ffi.string(self.c_method[0], self.method_len[0]).decode('ascii')
        path = ffi.string(self.c_path[0], self.path_len[0]).decode('ascii')
        version = "1." + str(self.minor_version[0])

        headers = {}
        for idx in range(self.num_headers[0]):
           header = self.c_headers[idx]
           name = ffi.string(header.name, header.name_len).decode('ascii').title()
           value = ffi.string(header.value, header.value_len).decode('latin1')
           headers[name] = value

        self.buffer = self.buffer[result:]

        self.request = HttpRequest(method, path, version, headers)

        self.on_headers(self.request)

        if self.minor_version[0] == 0:
            self.connection = self.request.headers.get('Connection', 'close')
            self.transfer = 'identity'
        else:
            self.connection = self.request.headers.get('Connection', 'keep-alive')
            self.transfer = self.request.headers.get('Transfer-Encoding', 'chunked')

        self.content_length = self.request.headers.get('Content-Length')
        if self.content_length is not None:
            self.content_length = int(self.content_length)

        return result

    def _parse_body(self):
        if self.content_length is None and self.request.method in NO_SEMANTICS:
            self.on_body(self.request)
            return 0
        elif self.content_length == 0:
            self.request.body = b""
            self.on_body(self.request)
            return 0
        elif self.content_length is not None:
            if self.content_length > len(self.buffer):
                return -2

            self.request.body = bytes(self.buffer[:self.content_length])
            self.on_body(self.request)
            self.buffer = self.buffer[self.content_length:]

            result = self.content_length

            return result
        elif self.transfer == 'identity':
            return -2
        elif self.transfer == 'chunked':
            if not self.chunked_decoder:
                self.chunked_decoder = ffi.new('struct phr_chunked_decoder*')
                self.chunked_decoder.consume_trailer = b'\x01'

            chunked_offset_start = self.chunked_offset[0]
            self.chunked_offset[0] = len(self.buffer) - self.chunked_offset[0]
            result = lib.phr_decode_chunked(
                self.chunked_decoder,
                ffi.from_buffer(self.buffer) + chunked_offset_start,
                self.chunked_offset)
            self.chunked_offset[0] = self.chunked_offset[0] + chunked_offset_start

            if result == -2:
                self.buffer = self.buffer[:self.chunked_offset[0]]
                return result
            elif result == -1:
                self.on_error('malformed_body')
                self._reset_state()
                self.buffer = bytearray()

                return result

            self.request.body = bytes(self.buffer[:self.chunked_offset[0]])
            self.on_body(self.request)
            self.buffer = self.buffer[
                self.chunked_offset[0]:self.chunked_offset[0] + result]
            self._reset_state()

            return result

    def feed(self, data):
        self.buffer += data

        while 1:
            if self.state == 'headers':
                result = self._parse_headers()

                if result <= 0:
                    return None

                self.state = 'body'

            if self.state == 'body':
                result = self._parse_body()

                if result < 0:
                    return None

                self.state = 'headers'

    def feed_disconnect(self):
        if not self.buffer:
            return

        if not self.transfer:
            self.on_error('incomplete_headers')
        elif self.transfer == 'identity':
            self.request.body = bytes(self.buffer)
            self.on_body(self.request)
        elif self.transfer == 'chunked':
            self.on_error('incomplete_body')

        self._reset_state()
        self.buffer = bytearray()

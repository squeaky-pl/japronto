from __future__ import print_function

from libpicohttpparser import ffi, lib


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

        self._reset_state()
        self.buffer = bytearray()

        self.c_method = ffi.new('char **')
        self.method_len = ffi.new('size_t *')
        self.c_path = ffi.new('char **')
        self.path_len = ffi.new('size_t *')
        self.minor_version = ffi.new('int *')
        self.c_headers = ffi.new('struct phr_header[10]')
        self.num_headers = ffi.new('size_t *')

    def _reset_state(self):
        self.request = None
        self.state = 'headers'
        self.connection = 'close'
        self.content_length = None
        self.chunked_decoder = None
        self.chunked_offset = None

    def parse_headers(self):
        self.num_headers[0] = 10

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

        return result

    def parse_body(self):
        if self.content_length == 0:
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
        elif self.connection == 'close':
            return -2
        # if we get here it means chunked
        elif self.connection == 'keep-alive':
            if not self.chunked_decoder:
                self.chunked_decoder = ffi.new('struct phr_chunked_decoder*')
                self.chunked_decoder.consume_trailer = b'\x01'
                self.chunked_offset = ffi.new('size_t*')

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

            return result

    def feed(self, data):
        self.buffer += data

        while 1:
            if self.state == 'headers':
                headers_result = self.parse_headers()

                if headers_result > 0:
                    if self.request.version == "1.0":
                        self.connection = self.request.headers.get('Connection', 'close')
                    else:
                        self.connection = self.request.headers.get('Connection', 'keep-alive')
                        self.content_length = self.request.headers.get('Content-Length')
                        if self.content_length is not None:
                            self.content_length = int(self.content_length)

                    self.state = 'body'
                else:
                    return None

            if self.state == 'body':
                body_result = self.parse_body()

                if body_result >= 0:
                    self.state = 'headers'
                elif body_result == -2:
                    return None


    def feed_disconnect(self):
        if self.connection == 'close':
            if self.request and self.buffer:
                self.request.body = bytes(self.buffer)
                self.on_body(self.request)
            elif not self.request and self.buffer:
                self.on_error('incomplete_headers')
        elif self.connection == 'keep-alive' and self.buffer:
                if self.content_length is not None and self.request.body or \
                   self.content_length == 0:
                   self.on_error('incomplete_headers')
                elif self.content_length is None and self.request.body:
                    self.on_error('incomplete_headers')
                else:
                    self.on_error('incomplete_body')

        self._reset_state()
        self.buffer = bytearray()

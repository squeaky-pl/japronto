from parser.libpicohttpparser import ffi, lib


class HttpRequestParser(object):
    def __init__(self, on_headers, on_body, on_error):
        self.on_headers = on_headers
        self.on_body = on_body
        self.on_error = on_error

        self.c_method = ffi.new('char **')
        self.method_len = ffi.new('size_t *')
        self.c_path = ffi.new('char **')
        self.path_len = ffi.new('size_t *')
        self.minor_version = ffi.new('int *')
        self.c_headers = ffi.new('struct phr_header[10]')
        self.num_headers = ffi.new('size_t *')
        self.chunked_offset = ffi.new('size_t*')

        self._reset_state(True)

    def _reset_state(self, disconnect=False):
        self.state = 'headers'
        self.transfer = None
        self.content_length = None
        self.chunked_decoder = None
        self.chunked_offset[0] = 0
        if disconnect:
            self.connection = None
            self.buffer = bytearray()

    def _parse_headers(self):
        if self.connection == 'close':
            self.on_error('excessive_data')
            self._reset_state(True)

            return -1

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
            self._reset_state(True)

            return result
        else:
            self._reset_state()

        method = ffi.cast(
            'char[{}]'.format(self.method_len[0]), self.c_method[0])
        path = ffi.cast(
            'char[{}]'.format(self.path_len[0]), self.c_path[0])
        headers = ffi.cast(
            "struct phr_header[{}]".format(self.num_headers[0]),
            self.c_headers)

        if ffi.buffer(method)[:] in (b'GET', b'DELETE', b'HEAD'):
            self.no_semantics = True

        if self.minor_version[0] == 0:
            self.connection = 'close'
        else:
            self.connection = 'keep-alive'

        for header in headers:
            header_name = ffi.string(header.name, header.name_len).title()
            # maybe len + strcasecmp C style is faster?
            if header_name == b'Transfer-Encoding':
                self.transfer = ffi.string(
                    header.value, header.value_len).decode('ascii')
                # FIXME comma separated and invalid values
            elif header_name == b'Connection':
                self.connection = ffi.string(
                    header.value, header.value_len).decode('ascii')
                # FIXME other options for Connection like updgrade
            elif header_name == b'Content-Length':
                content_length_error = False

                if not header.value_len:
                    content_length_error = True

                if not content_length_error:
                    content_length = ffi.buffer(header.value, header.value_len)

                if not content_length_error and content_length[0] in b'+-':
                    content_length_error = True

                if not content_length_error:
                    try:
                        self.content_length = int(content_length[:])
                    except ValueError:
                        content_length_error = True

                if content_length_error:
                    self.on_error('invalid_headers')
                    self._reset_state(True)

                    return -1

        self.on_headers(method, path, self.minor_version[0], headers)

        self.buffer = self.buffer[result:]

        return result

    def _parse_body(self):
        if self.content_length is None and self.transfer is None:
            self.on_body(None)
            return 0
        elif self.content_length == 0:
            self.on_body(ffi.from_buffer(b""))
            return 0
        elif self.content_length is not None:
            if self.content_length > len(self.buffer):
                return -2

            body = memoryview(self.buffer)[:self.content_length]
            self.on_body(ffi.from_buffer(body))
            self.buffer = self.buffer[self.content_length:]

            result = self.content_length

            return result
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
            self.chunked_offset[0] = self.chunked_offset[0] \
                + chunked_offset_start

            if result == -2:
                self.buffer = self.buffer[:self.chunked_offset[0]]
                return result
            elif result == -1:
                self.on_error('malformed_body')
                self._reset_state(True)

                return result

            body = memoryview(self.buffer)[:self.chunked_offset[0]]
            self.on_body(ffi.from_buffer(body))
            self.buffer = self.buffer[
                self.chunked_offset[0]:self.chunked_offset[0] + result]
            self._reset_state()

            return result

    def feed(self, data):
        self.buffer += data

        while self.buffer:
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
        if self.state == 'headers' and self.buffer:
            self.on_error('incomplete_headers')
        elif self.state == 'body':
            self.on_error('incomplete_body')

        self._reset_state(True)

import os.path

from libpicohttpparser import ffi, lib


class HttpRequest(object):
    def __init__(self, path, method, version, headers):
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
        self._reset()

    def _reset(self):
        self.request = None
        self.state = 'headers'
        self.connection = None
        self.content_length = None

        self._reset_buffer()

    def _reset_buffer(self):
        self.buffer = bytearray()
        self.buffer_consumed = 0
        self.buffer_len = 0
        self.c_buffer = None

    def parse_headers(self, data):
        c_method = ffi.new('char **')
        method_len = ffi.new('size_t *')
        c_path = ffi.new('char **')
        path_len = ffi.new('size_t *')
        minor_version = ffi.new('int *')
        c_headers = ffi.new('struct phr_header[10]')
        num_headers = ffi.new('size_t *')
        num_headers[0] = 10

        result = lib.phr_parse_request(
            self.c_buffer or ffi.from_buffer(self.buffer),
            self.buffer_len, c_method, method_len, c_path, path_len,
            minor_version, c_headers, num_headers, 0)

        if result == -2:
            if not self.c_buffer:
                self.c_buffer = ffi.new('char[8192]')
                ffi.memmove(self.c_buffer, self.buffer, self.buffer_len)

            return result
        if result == -1:
            self.on_error()
            self._reset()

            return result

        self.buffer_consumed += result

        method = ffi.string(c_method[0], method_len[0]).decode('ascii')
        path = ffi.string(c_path[0], path_len[0]).decode('ascii')
        version = "1." + str(minor_version[0])

        headers = {}
        for idx in range(num_headers[0]):
           header = c_headers[idx]
           name = ffi.string(header.name, header.name_len).decode('ascii')
           value = ffi.string(header.value, header.value_len).decode('latin1')
           headers[name] = value

        self.request = HttpRequest(method, path, version, headers)

        self.on_headers(self.request)

        return result

    def parse_body(self, data):
        if not self.body_parts and self.buffer_consumed < self.buffer_len:
            if self.buffer_owned:
                chunk = ffi.unpack(
                    self.buffer + self.buffer_consumed,
                    self.buffer_length - self.buffer_consumed)
            else:
               chunk = self.buffer[self.buffer_consumed:]

            self.body_parts.append(chunk)

        self.body_parts.append(data)


    def feed(self, data: bytes):
        if not self.c_buffer:
            self.buffer += data
        else:
            ffi.memmove(self.c_buffer + self.buffer_len, data, len(data))
        self.buffer_len += len(data)

        if(self.state == 'headers'):
            headers_result = self.parse_headers(data)

            if(headers_result > 0):
                self._reset_buffer()

                if self.request.version == "1.0":
                    self.connection = self.request.headers.get('Connection', 'close')
                else:
                    self.connection = self.request.headers.get('Connection', 'keep-alive')
                    self.content_length = self.request.headers.get('Content-Length')

                #self.state == 'body'
        elif(self.state == 'body'):
            self.parse_body()




    def feed_disconnect():
        pass

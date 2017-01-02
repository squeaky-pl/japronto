import socket
import urllib.parse
import json


def readline(sock):
    line = b''
    while not line.endswith(b'\r\n'):
        line += sock.recv(1)

    return line


def readexact(sock, size):
    data = b''
    while size:
        chunk = sock.recv(size)
        data += chunk
        size -= len(chunk)

    return data


class Response:
    def __init__(self, sock):
        self.sock = sock

        self.read_status_line()
        self.read_headers()
        self.read_body()

    def read_status_line(self):
        status_line = b''
        while not status_line:
            status_line = readline(self.sock).strip()
        _, self.status, self.reason = status_line.split(None, 2)
        self.status = int(self.status)

    def read_headers(self):
        self.headers = {}

        while 1:
            line = readline(self.sock).strip()
            if not line:
                break

            name, value = line.split(b':')
            name = name.strip().decode('ascii').title()
            value = value.strip().decode('latin1')
            self.headers[name] = value

    @property
    def encoding(self):
        content_type = self.headers.get('Content-Type')
        if not content_type:
            return 'latin1'

        _, *rest = [v.split('=') for v in content_type.split(';')]

        rest = {k.strip(): v.strip() for k, v in rest}

        return rest.get('charset')


    def read_body(self):
        self.body = readexact(self.sock, int(self.headers['Content-Length']))
        self.text = self.body.decode(self.encoding)

    @property
    def json(self):
        return json.loads(self.text)


class Connection:
    def __init__(self, addr):
        self.addr = addr
        self.sock = None

    def maybe_connect(self):
        if self.sock:
            return self.sock

        addr = self.addr.split(':')
        addr[1] = int(addr[1])
        addr = tuple(addr)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(addr)

        return self.sock

    def putline(self, line=None):
        line = line or b''
        sock = self.maybe_connect()
        if not isinstance(line, bytes):
            line = str(line).encode('latin1')
        sock.sendall(line + b'\r\n')

    def putclose(self, data):
        sock = self.maybe_connect()
        if not isinstance(data, bytes):
            data = str(data).encode('latin1')
        sock.sendall(data)
        self.close()

    def putrequest(self, method, path, query_string=None):
        url = urllib.parse.quote(path)
        if query_string is not None:
            url += '?' + urllib.parse.quote(query_string)

        request_line = "{method} {url} HTTP/1.1" \
            .format(method=method, url=url)
        self.putline(request_line)

    def putheader(self, name, value):
        header_line = name + ': ' + value
        self.putline(header_line)

    def endheaders(self, body=None):
        self.putline()
        if body:
            sock = self.maybe_connect()
            sock.sendall(body)

    def getresponse(self):
        return Response(self.sock)

    def close(self):
        self.sock.close()

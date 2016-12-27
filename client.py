import socket
import urllib.parse


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

    def read_body(self):
        self.body = readexact(self.sock, int(self.headers['Content-Length']))


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
        sock.sendall(line + b'\r\n')

    def putrequest(self, method, path, query_string=None):
        url = urllib.parse.quote(path)
        if query_string is not None:
            url += '?' + urllib.parse.quote(query_string)

        request_line = "{method} {url} HTTP/1.1" \
            .format(method=method, url=url).encode('ascii')
        self.putline(request_line)

    def putheader(self, name, value):
        header_line = name.encode('ascii') + b': ' + value.encode('latin1')
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

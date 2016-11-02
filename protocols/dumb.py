import asyncio
import impl_cext


response = [
    'HTTP/1.1 200 OK\r\n',
    'Connection: keep-alive\r\n',
    'Content-Type: text/plain; encoding=utf-8\r\n',
    'Content-Length: '
]


class HttpProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.parser = impl_cext.HttpRequestParser(
            self.on_headers, self.on_body, self.on_error)
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        self.parser.feed_disconnect()

    def data_received(self, data):
        self.parser.feed(data)

    def on_headers(self, request):
        return

    def on_body(self, request):
        if request.path == '/':
            data = response[:]
            response.append('12\r\n\r\nHello world!')

        self.transport.write(data.encode('utf-8'))


    def on_error(self, error):
        print(error)

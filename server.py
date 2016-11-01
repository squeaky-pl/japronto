import asyncio
import uvloop
import impl_cext


response = [
    b'HTTP/1.1 200 OK\r\n',
    b'Connection: keep-alive\r\n',
    b'Content-Length: '
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
        self.loop.create_task(handle_request(request, self.transport))

    def on_error(self, error):
        print(error)


class Response:
    __slots__ = ('status_code', 'mime_type', 'text', 'encoding')

    def __init__(self, status_code=200, text='', mime_type='text/plain', encoding='utf-8'):
        self.status_code = 200
        self.mime_type = mime_type
        self.text = text
        self.encoding = encoding

    def render(self):
        data = ['HTTP/1.1 ', str(self.status_code),  ' OK\r\n']
        data.append('Connection: keep-alive\r\n')
        body = self.text.encode(self.encoding)
        data.extend(['Content-Type: ', self.mime_type, '; encoding=', self.encoding, '\r\n'])
        data.extend(['Content-Length: ', str(len(body)), '\r\n\r\n'])

        return ''.join(data).encode(self.encoding) + body


async def handle_request(request, transport):
    if(request.path == '/'):
        response = Response(text='Hello world!')
    elif(request.path == '/dump'):
        response = Response()
        data = [
            'method: ', request.method, '\r\n',
            'path: ', request.path, '\r\n',
            'version: ', request.version, '\r\n',
            'headers:\r\n'
        ]

        for h, v in request.headers.items():
            data.extend([h, ': ', v, '\r\n'])
        response.text = ''.join(data)

    transport.write(response.render())




def serve():
    loop = uvloop.new_event_loop()

    server_coro = loop.create_server(
        lambda: HttpProtocol(loop), '0.0.0.0', 8080, reuse_port=True)

    server = loop.run_until_complete(server_coro)

    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    serve()

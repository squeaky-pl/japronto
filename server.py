import asyncio
import uvloop
import impl_cext


response = [
    b'HTTP/1.1 200 OK\r\n',
    b'Connection: keep-alive\r\n',
    b'Content-Length: '
]


class HttpProtocol(asyncio.Protocol):
    def __init__(self):
        self.parser = impl_cext.HttpRequestParser(
            self.on_headers, self.on_body, self.on_error)

    def connection_made(self, transport):
          self.transport = transport
    #     print('connection made')

    def connection_lost(self, exc):
        self.parser.feed_disconnect()

    def data_received(self, data):
        self.parser.feed(data)

    def on_headers(self, request):
        return

    def on_body(self, request):
        self.transport.writelines(response)
        if request.path == '/':
            self.transport.write(b'12\r\n\r\nHello world!')
        elif request.path == '/dump':
            data = [
                'method: ', request.method, '\r\n',
                'path: ', request.path, '\r\n',
                'version: ', request.version, '\r\n',
                'headers:\r\n'
            ]

            for h, v in request.headers.items():
                data.extend([h, ': ', v, '\r\n'])

            data = (''.join(data)).encode()
            self.transport.write(str(len(data)).encode() + b'\r\n\r\n')
            self.transport.write(data)

    def on_error(self, error):
        print(error)


def serve():
    loop = uvloop.new_event_loop()

    server_coro = loop.create_server(lambda: HttpProtocol(), '0.0.0.0', 8080)

    server = loop.run_until_complete(server_coro)

    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    serve()

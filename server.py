import asyncio
import uvloop
import impl_cext


response = [
    b'HTTP/1.1 200 OK\r\n',
    b'Connection: close\r\n',
    b'Content-Length: 3\r\n',
    b'\r\n',
    b'asd']


class HttpProtocol(asyncio.Protocol):
    def __init__(self):
        self.parser = impl_cext.HttpRequestParser(
            self.on_headers, self.on_body, self.on_error)

    def connection_made(self, transport):
        self.transport = transport
        print('connection made')

    def connection_lost(self, exc):
        print('connection lost')
        self.parser.feed_disconnect()

    def data_received(self, data):
        print('received', data)
        self.parser.feed(data)

    def on_headers(self, request):
        request.dump_headers()

    def on_body(self, request):
        print(request.body)

        self.transport.writelines(response)

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

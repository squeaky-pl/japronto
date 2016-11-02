import asyncio
import impl_cext


from responses.py import factory, dispose, Response


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


async def handle_request(request, transport):
    if(request.path == '/'):
        response = factory(text='Hello world!')
    elif(request.path == '/dump'):
        response = factory()
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

    dispose(response)

import asyncio
from asyncio.queues import Queue


from japronto.response.cresponse import Response
from japronto.protocol.cprotocol import Protocol as CProtocol

static_response = b"""HTTP/1.1 200 OK\r
Connection: keep-alive\r
Content-Length: 12\r
Content-Type: text/plain; encoding=utf-8\r
\r
Hello statc!
"""


def make_class(flavor):
    if flavor == 'c':
        return CProtocol

    from japronto.parser import cparser

    class HttpProtocol(asyncio.Protocol):
        def __init__(self, loop, handler):
            self.parser = cparser.HttpRequestParser(
                self.on_headers, self.on_body, self.on_error)
            self.loop = loop
            self.response = Response()

        if flavor == 'queue':
            def connection_made(self, transport):
                self.transport = transport
                self.queue = Queue(loop=self.loop)
                self.loop.create_task(handle_requests(self.queue, transport))
        else:
            def connection_made(self, transport):
                self.transport = transport

        def connection_lost(self, exc):
            self.parser.feed_disconnect()

        def data_received(self, data):
            self.parser.feed(data)

        def on_headers(self, request):
            return

        if flavor == 'block':
            def on_body(self, request):
                handle_request_block(request, self.transport, self.response)
        elif flavor == 'dump':
            def on_body(self, request):
                handle_dump(request, self.transport, self.response)
        elif flavor == 'task':
            def on_body(self, request):
                self.loop.create_task(handle_request(request, self.transport))
        elif flavor == 'queue':
            def on_body(self, request):
                self.queue.put_nowait(request)
        elif flavor == 'inline':
            def on_body(self, request):
                body = 'Hello inlin!'
                status_code = 200
                mime_type = 'text/plain'
                encoding = 'utf-8'
                text = [b'HTTP/1.1 ']
                text.extend([str(status_code).encode(), b' OK\r\n'])
                text.append(b'Connection: keep-alive\r\n')
                text.append(b'Content-Length: ')
                text.extend([str(len(body)).encode(), b'\r\n'])
                text.extend([
                    b'Content-Type: ', mime_type.encode(),
                    b'; encoding=', encoding.encode(), b'\r\n\r\n'])
                text.append(body.encode())

                self.transport.write(b''.join(text))

        elif flavor == 'static':
            def on_body(self, request):
                self.transport.write(static_response)

        def on_error(self, error):
            print(error)

    return HttpProtocol


async def handle_requests(queue, transport):
    while 1:
        await queue.get()

        response = Response(text='Hello queue!')

        transport.write(response.render())


async def handle_request(request, transport):
    response = Response(text='Hello ttask!')

    transport.write(response.render())


def handle_request_block(request, transport, response):
    response.__init__(404, text='Hello block')

    transport.write(response.render())


def handle_dump(request, transport, response):
    text = request.path
    response.__init__(text=text)

    transport.write(response.render())

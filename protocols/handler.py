import asyncio
from asyncio.queues import Queue
import impl_cext


#from responses.py import factory, dispose, Response
from responses.cresponse import Response


def make_class(flavor):
    class HttpProtocol(asyncio.Protocol):
        def __init__(self, loop):
            self.parser = impl_cext.HttpRequestParser(
                self.on_headers, self.on_body, self.on_error)
            self.loop = loop

        if flavor in ['block', 'task']:
            def connection_made(self, transport):
                self.transport = transport
        elif flavor == 'queue':
            def connection_made(self, transport):
                self.transport = transport
                self.queue = Queue(loop=self.loop)
                self.loop.create_task(handle_requests(self.queue, transport))

        def connection_lost(self, exc):
            self.parser.feed_disconnect()

        def data_received(self, data):
            self.parser.feed(data)

        def on_headers(self, request):
            return

        if flavor == 'block':
            def on_body(self, request):
                handle_request_block(request, self.transport)
        elif flavor == 'task':
            def on_body(self, request):
                self.loop.create_task(handle_request(request, self.transport))
        elif flavor == 'queue':
            def on_body(self, request):
                self.queue.put_nowait(request)

        def on_error(self, error):
            print(error)

    return HttpProtocol


async def handle_requests(queue, transport):
    while 1:
        request = await queue.get()

        if request.path == '/':
            response = Response(text='Hello queue!')

            transport.write(response.render())


async def handle_request(request, transport):
    if request.path == '/':
        response = Response(text='Hello ttask!')

    transport.write(response.render())


def handle_request_block(request, transport):
    if request.path == '/':
        response = Response(text='Hello block!')

    transport.write(response.render())

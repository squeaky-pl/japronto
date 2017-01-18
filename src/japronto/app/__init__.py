import signal
import asyncio
import traceback
import socket

import uvloop

from japronto.router import Router, RouteNotFoundException
from japronto.protocol.cprotocol import Protocol
from japronto.protocol.creaper import Reaper


class Application:
    def __init__(self, loop=None, reaper_settings=None, log_request=False):
        self._router = None
        self._loop = None
        self._connections = set()
        self._reaper_settings = reaper_settings or {}
        self._error_handlers = []
        self._log_request = log_request
        self._request_extensions = {}

    @property
    def loop(self):
        if not self._loop:
            self._loop = uvloop.new_event_loop()

        return self._loop

    @property
    def router(self):
        if not self._router:
            self._router = Router()

        return self._router

    def __finalize(self):
        self.loop
        self.router

        self._reaper = Reaper(self, **self._reaper_settings)
        self._matcher = self._router.get_matcher()

    def protocol_error_handler(self, error):
        print(error)

        error = error.encode('utf-8')

        response = [
            'HTTP/1.0 400 Bad Request\r\n',
            'Content-Type: text/plain; charset=utf-8\r\n',
            'Content-Length: {}\r\n\r\n'.format(len(error))]

        return ''.join(response).encode('utf-8') + error

    def default_request_logger(self, request):
        print(request.remote_addr, request.method, request.path)

    def add_error_handler(self, typ, handler):
        self._error_handlers.append((typ, handler))

    def default_error_handler(self, request, exception):
        if isinstance(exception, RouteNotFoundException):
            return request.Response(status_code=404, text='Not Found')
        if isinstance(exception, asyncio.CancelledError):
            return request.Response(status_code=503, text='Service unavailable')

        # FIXME traceback should be only available in debug mode
        tb = traceback.format_exception(None, exception, exception.__traceback__)
        tb = ''.join(tb)
        print(tb)
        return request.Response(status_code=500, text=tb)

    def error_handler(self, request, exception):
        for typ, handler in self._error_handlers:
            if typ is not None and not isinstance(exception, typ):
                continue

            try:
                return handler(request, exception)
            except:
                print('-- Exception in error_handler occured:')
                traceback.print_exc()

            print('-- while handling:')
            traceback.print_exception(None, exception, exception.__traceback__)
            return request.Response(
                status_code=500, text='Internal Server Error')

        return self.default_error_handler(request, exception)


    async def drain(self):
        print('Draining connections...')
        # TODO idle connections will close connection with half-read requests
        idle_connections = [c for c in self._connections if c.pipeline_empty]
        busy_connections = [c for c in self._connections if not c.pipeline_empty]
        for c in idle_connections:
            c.transport.close()
#       for c in busy_connections:
#            need to implement something that makes protocol.on_data
#            start rejecting incoming data
#            this closes transposrt unfortunately
#            sock = c.transport.get_extra_info('socket')
#            sock.shutdown(socket.SHUT_RD)

        if idle_connections:
            print('{} idle connections closed immediately'
                .format(len(idle_connections)))
        if busy_connections:
            print('{} connections busy, read-end closed'
                .format(len(busy_connections)))
        else:
            return

        for x in range(5, 0, -1):
            await asyncio.sleep(1)
            idle_connections = [c for c in self._connections if c.pipeline_empty]
            for c in idle_connections:
                c.transport.close()
            busy_connections = [c for c in self._connections if not c.pipeline_empty]
            if not busy_connections:
                break
            else:
                print("{} seconds remaining, {} connections still busy".format(x, len(busy_connections)))

        busy_connections = [c for c in self._connections if not c.pipeline_empty]
        if busy_connections:
            print('Forcefully killing {} connections'.format(len(busy_connections)))
        for c in busy_connections:
            c.pipeline_cancel()

    def extend_request(self, handler, *, name=None, property=False):
        if not name:
            name = handler.__name__

        self._request_extensions[name] = (handler, property)


    def serve(self, protocol_factory=None, reuse_port=False):
        self.__finalize()

        loop = self.loop
        asyncio.set_event_loop(loop)

        protocol_factory = protocol_factory or Protocol

        server_coro = loop.create_server(
            lambda: protocol_factory(self),
            '0.0.0.0', 8080, reuse_port=reuse_port)

        server = loop.run_until_complete(server_coro)

        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        loop.add_signal_handler(signal.SIGINT, loop.stop)
        try:
            loop.run_forever()
        finally:
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.run_until_complete(self.drain())
            self._reaper.stop()
            loop.close()

            # break reference and cleanup matcher buffer
            del self._matcher

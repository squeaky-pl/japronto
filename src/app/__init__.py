import signal
import asyncio
import traceback

import router
import uvloop
import router.cmatcher

from protocol.cprotocol import Protocol as CProtocol
from protocol.creaper import Reaper

class Application:
    def __init__(self, loop=None, reaper_settings=None):
        self._router = None
        self._loop = None
        self._connections = set()
        self._reaper_settings = reaper_settings or {}
        self._error_handlers = []

    def get_loop(self):
        if not self._loop:
            self._loop = uvloop.new_event_loop()

        return self._loop

    def get_router(self):
        if not self._router:
            self._router = router.Router(router.cmatcher.Matcher)

        return self._router

    def __freeze(self):
        self.get_loop()
        self.get_router()
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

    def add_error_handler(self, typ, handler):
        self._error_handlers.append((typ, handler))

    def default_error_handler(self, request, exception):
        tb = traceback.format_exception(None, exception, exception.__traceback__)
        tb = ''.join(tb)
        print(tb)
        return request.Response(status_code=500, text=tb)

    def error_handler(self, request, exception):
        for typ, handler in self._error_handlers:
            if typ is None or isinstance(exception, typ):
                try:
                    return handler(request, exception)
                except:
                    print('Exception in error_handler')
                    break

        return self.default_error_handler(request, exception)

    def serve(self, protocol_factory=None, reuse_port=False):
        self.__freeze()

        loop = self.get_loop()
        protocol_factory = protocol_factory or CProtocol

        asyncio.set_event_loop(loop)

        server_coro = loop.create_server(
            lambda: protocol_factory(self),
            '0.0.0.0', 8080, reuse_port=reuse_port)

        server = loop.run_until_complete(server_coro)

        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        loop.add_signal_handler(signal.SIGINT, loop.stop)
        try:
            loop.run_forever()
        finally:
            self._reaper.stop()
            loop.close()

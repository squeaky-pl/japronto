import signal

import router
import uvloop
import router.cmatcher


class Application:
    def __init__(self, loop=None):
        self._router = None
        self._loop = None

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

        self._matcher = self._router.get_matcher()

    def error_handler(self, request, transport, response):
        response.__init__(400, text='Something went wrong')

        transport.write(response.render())


    def serve(self, protocol_factory, reuse_port=False):
        self.__freeze()

        loop = self.get_loop()

        server_coro = loop.create_server(
            lambda: protocol_factory(self),
            '0.0.0.0', 8080, reuse_port=reuse_port)

        server = loop.run_until_complete(server_coro)

        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        loop.add_signal_handler(signal.SIGINT, loop.stop)
        try:
            loop.run_forever()
        finally:
            loop.close()

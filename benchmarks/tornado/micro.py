from tornado import ioloop, web
from tornado.httputil import HTTPHeaders, responses
from tornado.platform.asyncio import AsyncIOMainLoop
import asyncio
import uvloop


loop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)
AsyncIOMainLoop().install()


class MainHandler(web.RequestHandler):
    def get(self):
        self.write('Hello world!')

    # skip calculating ETag, ~8% faster
    def set_etag_header(self):
         pass

    def check_etag_header(self):
         return False

    # torando sends Server and Date headers by default, ~4% faster
    def clear(self):
        self._headers = HTTPHeaders(
            {'Content-Type': 'text/plain; charset=utf-8'})
        self._write_buffer = []
        self._status_code = 200
        self._reason = responses[200]

app = web.Application([('/', MainHandler)])

app.listen(8080)

loop.run_forever()

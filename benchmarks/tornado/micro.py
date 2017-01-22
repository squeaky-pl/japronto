from tornado import ioloop, web


class MainHandler(web.RequestHandler):
    def get(self):
        self.write('Hello world!')

    # skip calculating ETag, makes tornado ~8% faster
    def set_etag_header(self):
         pass

    def check_etag_header(self):
         return False


app = web.Application([('/', MainHandler)], debug=False,
    compress_response=False,
    static_hash_cache=False)

app.listen(8080)
ioloop.IOLoop.current().start()

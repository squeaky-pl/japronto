import asyncio
import uvloop
import argparse
import sys

import protocol.handler


from router.cmatcher import Matcher
from router import Router
from app import Application


def slash(request, transport, response):
    response.__init__(text='Hello slash!')

    transport.write(response.render())


def hello(request, transport, response):
    response.__init__(text='Hello hello!')

    transport.write(response.render())


def dump(request, transport, response):
    text = """
Method: {0.method}
Path: {0.path}
Version: {0.version}
Headers: {0.headers}
""".strip().format(request)

    response.__init__(text=text)

    transport.write(response.render())


app = Application()

r = app.get_router()
r.add_route('/', slash)
r.add_route('/hello', hello)
r.add_route('/dump', dump)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser('server')
    argparser.add_argument(
        '-p', dest='flavor', default='block')
    args = argparser.parse_args(sys.argv[1:])

    app.serve(protocol.handler.make_class(args.flavor))

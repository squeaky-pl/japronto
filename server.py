import asyncio
import uvloop
import argparse
import sys

import protocol.handler


from router.cmatcher import Matcher
from router import Router
from app import Application


def slash(request, response):
    response.__init__(text='Hello slash!')

    return response


def hello(request, response):
    response.__init__(text='Hello hello!')

    return response


async def sleep(request, response):
    await asyncio.sleep(3)
    response.__init__(text='I am sleepy')

    return response


async def loop(request, response):
    i = 0
    while i < 10:
        await asyncio.sleep(1)
        print(i)
        i += 1

    response.__init__(text='Loop finished')

    return response



def dump(request, response):
    text = """
Method: {0.method}
Path: {0.path}
Version: {0.version}
Headers: {0.headers}
""".strip().format(request)

    response.__init__(text=text)

    return response


app = Application()

r = app.get_router()
r.add_route('/', slash)
r.add_route('/hello', hello)
r.add_route('/dump', dump)
r.add_route('/sleep', sleep)
r.add_route('/loop', loop)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser('server')
    argparser.add_argument(
        '-p', dest='flavor', default='block')
    args = argparser.parse_args(sys.argv[1:])

    app.serve(protocol.handler.make_class(args.flavor))

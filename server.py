import asyncio
import uvloop
import argparse
import sys

import protocol.handler


from router.cmatcher import Matcher
from router import Router
from app import Application


def slash(request):
    return request.Response(text='Hello slash!')


def hello(request):
    return request.Response(text='Hello hello!')


async def sleep(request):
    await asyncio.sleep(3)
    return request.Response(text='I am sleepy')


async def loop(request):
    i = 0
    while i < 10:
        await asyncio.sleep(1)
        print(i)
        i += 1

    return request.Response(text='Loop finished')


def dump(request):
    text = """
Method: {0.method}
Path: {0.path}
Version: {0.version}
Headers: {0.headers}
Match: {0.match_dict}
Body: {0.body}
QS: {0.query_string}
""".strip().format(request)

    return request.Response(text=text)


app = Application()

r = app.get_router()
r.add_route('/', slash)
r.add_route('/hello', hello)
r.add_route('/dump/{this}/{that}', dump)
r.add_route('/sleep/{pinch}', sleep)
r.add_route('/loop', loop)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser('server')
    argparser.add_argument(
        '-p', dest='flavor', default='block')
    args = argparser.parse_args(sys.argv[1:])

    app.serve(protocol.handler.make_class(args.flavor))

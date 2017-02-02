import asyncio
import argparse
import os.path
import sys
import socket

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../src'))

import japronto.protocol.handler  # noqa
from japronto.router.cmatcher import Matcher  # noqa
from japronto.router import Router  # noqa
from japronto.app import Application  # noqa


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
    sock = request.transport.get_extra_info('socket')
    no_delay = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
    text = """
Method: {0.method}
Path: {0.path}
Version: {0.version}
Headers: {0.headers}
Match: {0.match_dict}
Body: {0.body}
QS: {0.query_string}
query: {0.query}
mime_type: {0.mime_type}
encoding: {0.encoding}
form: {0.form}
keep_alive: {0.keep_alive}
no_delay: {1}
route: {0.route}
""".strip().format(request, no_delay)

    return request.Response(text=text, headers={'X-Version': '123'})


app = Application()

r = app.router
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

    app.run(protocol_factory=japronto.protocol.handler.make_class(args.flavor))

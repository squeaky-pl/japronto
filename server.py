import asyncio
import uvloop
import signal
import argparse
import sys

import protocols.dumb
import protocols.handler


def serve(protocol_factory, reuse_port=False):
    loop = uvloop.new_event_loop()

    server_coro = loop.create_server(
        lambda: protocol_factory(loop),
        '0.0.0.0', 8080, reuse_port=reuse_port)

    server = loop.run_until_complete(server_coro)

    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser('server')
    argparser.add_argument(
        '-p', dest='protocol_factory', default='handler')
    args = argparser.parse_args(sys.argv[1:])

    serve(getattr(protocols, args.protocol_factory).HttpProtocol)

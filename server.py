import asyncio
import uvloop
import signal
import argparse
import sys

import protocols.handler


def serve(protocol_factory, reuse_port=False):
    loop = uvloop.new_event_loop()

    server_coro = loop.create_server(
        lambda: protocol_factory(loop, protocols.handler.handle_request_block),
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
        '-p', dest='flavor', default='block')
    args = argparser.parse_args(sys.argv[1:])

    serve(protocols.handler.make_class(args.flavor))

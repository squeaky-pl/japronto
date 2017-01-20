from argparse import ArgumentParser, SUPPRESS
from importlib import import_module

from .app import Application


def get_parser():
    parser = ArgumentParser(prog='python -m japronto')
    parser.add_argument('--host', dest='host', type=str, default='0.0.0.0')
    parser.add_argument('--port', dest='port', type=int, default=8080)
    parser.add_argument('--worker-num', dest='worker_num', type=int, default=1)
    parser.add_argument(
        '--reload', dest='reload', action='store_const',
        const=True, default=False)

    parser.add_argument(
        '--reloader-pid', dest='reloader_pid', type=int, help=SUPPRESS)

    parser.add_argument('application')

    return parser


def verify(args):
    try:
        module, attribute = args.application.rsplit('.', 1)
    except ValueError:
        print(
            "Application specificer must contain at least one '.', got '{}'."
            .format(args.application))
        return False

    try:
        module = import_module(module)
    except ModuleNotFoundError as e:
        print(e.args[0] + ' on Python search path.')
        return False

    try:
        attribute = getattr(module, attribute)
    except AttributeError:
        print("Module '{}' does not have an attribute '{}'."
            .format(module.__name__, attribute))
        return False

    if not isinstance(attribute, Application):
        print("{} is not an instance of 'japronto.Application'.")
        return False

    return attribute


def run(attribute, args):
    attribute._run(
        host=args.host, port=args.port,
        worker_num=args.worker_num, reloader_pid=args.reloader_pid)

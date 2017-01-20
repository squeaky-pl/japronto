from argparse import ArgumentParser
from importlib import import_module
import sys

from .app import Application


def main():
    parser = ArgumentParser(prog='python -m japronto')
    parser.add_argument('--host', dest='host', type=str, default='0.0.0.0')
    parser.add_argument('--port', dest='port', type=int, default=8080)
    parser.add_argument('--worker-num', dest='worker_num', type=int, default=1)
    parser.add_argument('application')

    args = parser.parse_args()

    try:
        module, attribute = args.application.rsplit('.', 1)
    except ValueError:
        print(
            "Application specificer must contain at least one '.', got '{}'."
            .format(args.application))
        return 1

    try:
        module = import_module(module)
    except ModuleNotFoundError as e:
        print(e.args[0] + ' on Python search path.')
        return 1

    try:
        attribute = getattr(module, attribute)
    except AttributeError:
        print("Module '{}' does not have an attribute '{}'."
            .format(module.__name__, attribute))
        return 1

    if not isinstance(attribute, Application):
        print("{} is not an instance of 'japronto.Application'.")
        return 1

    attribute.run()


sys.exit(main())

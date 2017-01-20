import sys
import os

from .runner import get_parser, verify, run


def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.reload:
        os.execv(
            sys.executable,
            [sys.executable, '-m', 'japronto.reloader', *sys.argv[1:]])

    attribute = verify(args)
    if not attribute:
        return 1

    run(attribute, args)


sys.exit(main())

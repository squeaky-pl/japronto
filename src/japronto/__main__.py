import sys
import os

from .runner import get_parser, verify, run


def main():
    parser = get_parser()
    args = parser.parse_args()

    if not args.script:
        os.putenv('_JAPR_IGNORE_RUN', '1')

    if args.reload:
        os.execv(
            sys.executable,
            [sys.executable, '-m', 'japronto.reloader', *sys.argv[1:]])

    if not args.script:
        os.environ['_JAPR_IGNORE_RUN'] = '1'

    attribute = verify(args)
    if not attribute:
        return 1

    run(attribute, args)


sys.exit(main())

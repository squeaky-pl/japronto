import sys

from .runner import get_parser, verify, run


def main():
    parser = get_parser()
    args = parser.parse_args()

    attribute = verify(args)
    if not attribute:
        return 1

    run(attribute, args)


sys.exit(main())

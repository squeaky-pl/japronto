from distutils.core import Extension


def get_extension():
    return Extension(
        'japronto.parser.cparser',
        sources=['cparser.c'],
        include_dirs=['../../picohttpparser'],
        extra_objects=['src/picohttpparser/picohttpparser.o'],
        define_macros=[('PARSER_STANDALONE', 1)])

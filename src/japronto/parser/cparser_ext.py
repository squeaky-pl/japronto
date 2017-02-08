from distutils.core import Extension


def get_extension():
    return Extension(
        'japronto.parser.cparser',
        sources=['cparser.c', '../cpu_features.c'],
        include_dirs=['../../picohttpparser', '..'],
        extra_objects=[
            'src/picohttpparser/picohttpparser.o',
            'src/picohttpparser/ssepicohttpparser.o'],
        define_macros=[('PARSER_STANDALONE', 1)])

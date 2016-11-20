from distutils.core import Extension


def get_extension():
    return Extension(
        'parser.cparser',
        sources=['cparser.c'],
        libraries=['picohttpparser'],
        include_dirs=['../picohttpparser'],
        library_dirs=['../picohttpparser'],
        runtime_library_dirs=['../picohttpparser'],
        define_macros=[('PARSER_STANDALONE', 1)])

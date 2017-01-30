from distutils.core import Extension


def get_extension():
    # FIXME: terrible hack here
    runtime_library_dirs = '../../picohttpparser'
    if system.relative_source:
        runtime_library_dirs = '$ORIGIN/' + runtime_library_dirs
        import subprocess
        subprocess.check_call('cd src/picohttpparser && ./build', shell=True)

    return Extension(
        'japronto.parser.cparser',
        sources=['cparser.c'],
        libraries=['picohttpparser'],
        include_dirs=['../../picohttpparser'],
        library_dirs=['../../picohttpparser'],
        runtime_library_dirs=[runtime_library_dirs],
        define_macros=[('PARSER_STANDALONE', 1)])

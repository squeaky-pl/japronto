from distutils.core import Extension


def get_extension(fix_path):
    return Extension(
        'parser.cparser',
        sources=[fix_path('cparser.c')],
        libraries=['picohttpparser'],
        include_dirs=[fix_path('../picohttpparser')],
        library_dirs=[fix_path('../picohttpparser')],
        extra_link_args=['-Wl,-rpath,' + fix_path('../picohttpparser')],
        extra_compile_args=['-DPARSER_STANDALONE'])

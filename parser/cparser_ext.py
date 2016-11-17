from distutils.core import Extension

import os.path

here_path = os.path.dirname(__file__)

pico_path = os.path.abspath(os.path.join(here_path, '../picohttpparser'))


def get_extension():
    return Extension(
        'cparser',
        sources=[os.path.join(here_path, 'cparser.c')],
        libraries=['picohttpparser'],
        include_dirs=[pico_path],
        library_dirs=[pico_path],
        extra_link_args=['-Wl,-rpath,' + pico_path],
        extra_compile_args=['-DPARSER_STANDALONE'])

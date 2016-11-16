from distutils.core import setup, Extension

import os.path
import sys

shared_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../picohttpparser'))

cparser = Extension(
    'cparser', sources=['cparser.c'],
    libraries=['picohttpparser'], include_dirs=[shared_path],
    library_dirs=[shared_path], extra_link_args=['-Wl,-rpath,' + shared_path],
    extra_compile_args=['-DPARSER_STANDALONE'])

setup(
    name='cparser', version='1.0', description='Parse request',
    ext_modules=[cparser])

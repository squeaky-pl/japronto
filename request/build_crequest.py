from distutils.core import setup, Extension

import os.path
import sys

shared_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../picohttpparser'))

crequest = Extension(
    'crequest', sources=['crequest.c'],
    libraries=[], include_dirs=[shared_path],
    library_dirs=[], extra_link_args=[],
    extra_compile_args=[])

setup(
    name='crequest', version='1.0', description='',
    ext_modules=[crequest])

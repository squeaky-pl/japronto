from distutils.core import setup, Extension

import os.path
import sys

crequest = Extension(
    'crequest', sources=['crequest.c'],
    libraries=[], include_dirs=[],
    library_dirs=[], extra_link_args=[],
    extra_compile_args=[])

setup(
    name='crequest', version='1.0', description='',
    ext_modules=[crequest])

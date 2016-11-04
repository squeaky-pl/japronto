from distutils.core import setup, Extension

import os.path


cprotocol = Extension(
    'cprotocol', sources=['cprotocol.c'],
    libraries=[], include_dirs=[],
    library_dirs=[], extra_link_args=[],
    extra_compile_args=[])

setup(
    name='cprotocol', version='1.0', description='Protocol',
    ext_modules=[cprotocol])

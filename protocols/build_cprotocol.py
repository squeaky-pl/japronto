from distutils.core import setup, Extension

import os.path

shared_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../picohttpparser'))


cprotocol = Extension(
    'cprotocol', sources=['cprotocol.c', '../impl_cext.c'],
    libraries=['picohttpparser'], include_dirs=['.', '..', shared_path],
    library_dirs=[shared_path], extra_link_args=['-Wl,-rpath,' + shared_path],
    extra_compile_args=[])

setup(
    name='cprotocol', version='1.0', description='Protocol',
    ext_modules=[cprotocol])

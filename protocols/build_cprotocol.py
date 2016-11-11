from distutils.core import setup, Extension

import os.path

shared_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../picohttpparser'))

matcher_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../router')
)

matcher_lib = matcher_path + '/cmatcher.cpython-35m-x86_64-linux-gnu.so'

cprotocol = Extension(
    'cprotocol', sources=['cprotocol.c', '../impl_cext.c'],
    libraries=['picohttpparser'], include_dirs=['.', '..', '../router', shared_path, '../request'],
    library_dirs=[shared_path, matcher_path], extra_link_args=['-flto', '-Wl,-rpath,' + shared_path, '-Wl,-rpath,' + matcher_path, '-l:cmatcher.cpython-35m-x86_64-linux-gnu.so'],
    extra_compile_args=['-flto', '-O3', '-march=native'])

setup(
    name='cprotocol', version='1.0', description='Protocol',
    ext_modules=[cprotocol])

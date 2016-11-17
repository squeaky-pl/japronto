from distutils.core import setup, Extension

import os.path

shared_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../picohttpparser'))

matcher_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../router')
)

request_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../request')
)


matcher_lib = '-l:cmatcher.cpython-35m-x86_64-linux-gnu.so'
request_lib = '-l:crequest.cpython-35m-x86_64-linux-gnu.so'


cprotocol = Extension(
    'cprotocol', sources=['cprotocol.c', '../parser/cparser.c'],
    libraries=['picohttpparser'], include_dirs=['.', '../parser', '../router', shared_path, '../request'],
    library_dirs=[shared_path, matcher_path, request_path], extra_link_args=['-flto', '-Wl,-rpath,' + shared_path, '-Wl,-rpath,' + matcher_path, matcher_lib, '-Wl,-rpath,' + request_path, request_lib],
    extra_compile_args=['-flto', '-O3', '-march=native'])

setup(
    name='cprotocol', version='1.0', description='Protocol',
    ext_modules=[cprotocol])

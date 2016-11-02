from distutils.core import setup, Extension

import os.path



cresponse = Extension(
    'cresponse', sources=['cresponse.c'],
    libraries=[], include_dirs=[],
    library_dirs=[], extra_link_args=[],
    extra_compile_args=[])

setup(
    name='cresponse', version='1.0', description='Response',
    ext_modules=[cresponse])

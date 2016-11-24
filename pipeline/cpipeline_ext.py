from distutils.core import Extension
import os.path


def get_extension():
    return Extension(
        'pipeline.cpipeline',
        sources=['cpipeline.c', '../capsule.c'],
        include_dirs=['..'],
        libraries=[], library_dirs=[],
        extra_link_args=[],
        define_macros=[])

from distutils.core import Extension


def get_extension():
    return Extension(
        'japronto.pipeline.cpipeline',
        sources=['cpipeline.c'],
        include_dirs=[],
        libraries=[], library_dirs=[],
        extra_link_args=[],
        define_macros=[('PIPELINE_OPAQUE', 1)])

from distutils.core import Extension


def get_extension():
    return Extension(
        'protocol.generator',
        sources=['generator.c'],
        include_dirs=[],
        define_macros=[('GENERATOR_OPAQUE', 1)])

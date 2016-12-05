from distutils.core import Extension


def get_extension():
    return Extension(
        'protocol.generator',
        sources=['generator.c', '../capsule.c'],
        include_dirs=['..'])

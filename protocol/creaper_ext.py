from distutils.core import Extension


def get_extension():
    return Extension(
        'protocol.creaper',
        sources=['creaper.c'],
        include_dirs=[])

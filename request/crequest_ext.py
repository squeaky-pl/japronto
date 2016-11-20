from distutils.core import Extension


def get_extension():
    return Extension(
        'request.crequest',
        sources=['crequest.c', '../capsule.c'],
        include_dirs=['../picohttpparser', '..'])

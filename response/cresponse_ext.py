from distutils.core import Extension


def get_extension():
    return Extension(
        'response.cresponse',
        sources=['cresponse.c', '../capsule.c'],
        include_dirs=['..'])

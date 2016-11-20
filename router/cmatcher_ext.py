from distutils.core import Extension


def get_extension():
    return Extension(
        'router.cmatcher',
        sources=['cmatcher.c', '../capsule.c'],
        include_dirs=['../request', '..'])

from distutils.core import Extension


def get_extension(fix_path):
    return Extension(
        'router.cmatcher',
        sources=[fix_path('cmatcher.c')],
        include_dirs=[fix_path('../request')])

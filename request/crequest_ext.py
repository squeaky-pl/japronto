from distutils.core import Extension


def get_extension(fix_path):
    return Extension(
        'request.crequest',
        sources=[fix_path('crequest.c')],
        include_dirs=[fix_path('../picohttpparser')])

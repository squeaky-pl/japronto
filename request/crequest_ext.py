from distutils.core import Extension


def get_extension(fix_path):
    return Extension(
        'request.crequest',
        sources=[fix_path('crequest.c'), fix_path('../capsule.c')],
        include_dirs=[fix_path('../picohttpparser'), fix_path('..')])

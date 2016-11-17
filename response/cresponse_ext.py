from distutils.core import Extension


def get_extension(fix_path):
    return Extension(
        'response.cresponse',
        sources=[fix_path('cresponse.c')])

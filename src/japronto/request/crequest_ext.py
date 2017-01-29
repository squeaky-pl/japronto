from distutils.core import Extension


def get_extension():
    return Extension(
        'japronto.request.crequest',
        sources=['crequest.c', '../response/cresponse.c',
                 '../router/match_dict.c', '../capsule.c'],
        include_dirs=['../../picohttpparser', '..',
                      '../response', '../router'],
        define_macros=[('REQUEST_OPAQUE', 1)])

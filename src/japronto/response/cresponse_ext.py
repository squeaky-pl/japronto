from distutils.core import Extension


def get_extension():
    define_macros = [('RESPONSE_OPAQUE', 1)]
    if system.args.enable_response_cache:
        define_macros.append(('RESPONSE_CACHE', 1))

    return Extension(
        'japronto.response.cresponse',
        sources=['cresponse.c', '../capsule.c'],
        include_dirs=['..'],
        define_macros=define_macros)

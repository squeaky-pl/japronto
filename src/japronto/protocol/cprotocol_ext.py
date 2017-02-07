from distutils.core import Extension


def get_extension():
    cparser = system.get_extension_by_path('japronto/parser/cparser_ext.py')
    cpipeline = system.get_extension_by_path(
        'japronto/pipeline/cpipeline_ext.py')

    define_macros = [('PIPELINE_PAIR', 1)]
    if system.args.enable_reaper:
        define_macros.append(('REAPER_ENABLED', 1))

    return Extension(
        'japronto.protocol.cprotocol',
        sources=[
            'cprotocol.c', '../capsule.c', '../request/crequest.c',
            '../response/cresponse.c',
            *cparser.sources, *cpipeline.sources],
        include_dirs=[
            '.', '..', '../parser', '../pipeline',
            '../router', '../request',
            '../response', *cparser.include_dirs],
        extra_objects=cparser.extra_objects,
        define_macros=define_macros)

from distutils.core import Extension
import os.path


def get_extension():
    cparser = system.get_extension_by_path('japronto/parser/cparser_ext.py')
    cpipeline = system.get_extension_by_path('japronto/pipeline/cpipeline_ext.py')

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
            '../response', *cparser.include_dirs, '../../picoev'],
        runtime_library_dirs=['../../picoev'],
        libraries=[*cparser.libraries, 'picoev'], library_dirs=[*cparser.library_dirs, '../../picoev'],
        extra_link_args=cparser.extra_link_args,
        define_macros=define_macros)

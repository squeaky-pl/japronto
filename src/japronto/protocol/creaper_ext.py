from distutils.core import Extension


def get_extension():
    define_macros = [('PIPELINE_PAIR', 1)]
    if system.args.enable_reaper:
        define_macros.append(('REAPER_ENABLED', 1))

    return Extension(
        'japronto.protocol.creaper',
        sources=['creaper.c', '../capsule.c'],
        include_dirs=[
            '../parser', '../../picohttpparser',
            '../pipeline', '../request',
            '../router', '../response', '..'],
        define_macros=define_macros)

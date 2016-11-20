from distutils.core import Extension
import parser.cparser_ext
import os.path


def get_extension(fix_path):
    def parser_fix_path(path):
        return fix_path(os.path.join('../parser', path))

    cparser = parser.cparser_ext.get_extension(parser_fix_path)

    return Extension(
        'protocol.cprotocol',
        sources=[fix_path('cprotocol.c'), fix_path('../capsule.c'), *cparser.sources],
        include_dirs=[fix_path('.'), fix_path('..'), fix_path('../parser'), fix_path('../router'), fix_path('../request'), *cparser.include_dirs],
        libraries=cparser.libraries, library_dirs=cparser.library_dirs,
        extra_link_args=cparser.extra_link_args,
        extra_compile_args=['-DREAPER_ENABLED'])

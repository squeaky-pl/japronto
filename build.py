import argparse
import distutils
from distutils.command.build_ext import build_ext, CompileError
from distutils.core import Distribution
from glob import glob
import os.path
import shutil
import sysconfig
import os
import sys
import subprocess
try:
    import pytoml
except ImportError:
    pytoml = None
import runpy


SRC_LOCATION = 'src'
sys.path.insert(0, SRC_LOCATION)


class BuildSystem:
    def __init__(self, args, relative_source=False):
        self.args = args
        self.dest = self.args.dest
        self.relative_source = relative_source

    def get_extension_by_path(self, path):
        path = SRC_LOCATION + '/' + path
        result = runpy.run_path(path, {'system': self})
        extension = result['get_extension']()

        base_path = os.path.dirname(path)

        def fix_path(p):
            if os.path.isabs(p):
                return p

            return os.path.abspath(os.path.join(base_path, p))

        attrs = ['sources', 'include_dirs', 'library_dirs',
                 'runtime_library_dirs']
        for attr in attrs:
            val = getattr(extension, attr)
            if not val:
                continue

            if attr == 'sources' and self.relative_source:
                val = [
                    (os.path.normpath(os.path.join(base_path, v))
                     if not v.startswith('src')
                     else v) for v in val]
            elif attr == 'runtime_library_dirs' and self.relative_source:
                pass
            else:
                val = [fix_path(v) for v in val]
            if attr == 'runtime_library_dirs':
                setattr(extension, attr, None)
                attr = 'extra_link_args'
                val = ['-Wl,-rpath,' + v for v in val]
                val = (getattr(extension, attr) or []) + val
            setattr(extension, attr, val)

        return extension

    def discover_extensions(self):
        self.extensions = []

        ext_files = glob(SRC_LOCATION + '/**/*_ext.py', recursive=True)
        ext_files = [os.path.relpath(p, SRC_LOCATION) for p in ext_files]
        self.extensions = [self.get_extension_by_path(f) for f in ext_files]

        return self.extensions

    def dest_folder(self, mod_name):
        return self.dest + '/' + '/'.join(mod_name.split('.')[:-1])

    def build_toml(self, mod_name):
        return self.dest + '/' + '/'.join(mod_name.split('.')) + '.build.toml'

    def get_so(self, ext):
        return self.dest + '/' + '/'.join(ext.name.split('.')) + '.' + \
            sysconfig.get_config_var('SOABI') + '.so'

    def flags_changed(self, ext):
        toml = self.build_toml(ext.name)
        if not os.path.exists(toml):
            return True

        with open(toml) as f:
            flags = pytoml.load(f)

        ext_flags = {
            "extra_compile_args": ext.extra_compile_args,
            "extra_link_args": ext.extra_link_args,
            "define_macros": dict(ext.define_macros),
            "sources": ext.sources}

        return flags != ext_flags

    def should_rebuild(self, ext):
        so = self.get_so(ext)
        if not os.path.exists(so):
            return True

        so_mtime = os.stat(so).st_mtime

        includes = get_includes(ext)
        input_mtimes = [os.stat(s).st_mtime for s in ext.sources + includes]

        if max(input_mtimes) > so_mtime:
            return True

        if self.flags_changed(ext):
            return True

        return False


def prune(dest):
    paths = glob(os.path.join(dest, '.build/**/*.o'), recursive=True)
    paths.extend(glob(os.path.join(dest, '.build/**/*.so'), recursive=True))
    for path in paths:
        os.remove(path)


def profile_clean():
    paths = glob('build/**/*.gcda', recursive=True)
    for path in paths:
        os.remove(path)


def get_includes(ext):
    includes = []

    include_base = SRC_LOCATION + '/' + '/'.join(ext.name.split('.')[:-1])
    include_paths = [os.path.join(include_base, i) for i in ext.include_dirs]

    for source in ext.sources:
        with open(source) as f:
            for line in f:
                line = line.strip()
                if not line.startswith('#include'):
                    continue

                header = line.split()[1][1:-1]
                for path in include_paths:
                    if not os.path.exists(os.path.join(path, header)):
                        continue

                    includes.append(os.path.join(path, header))
                    break

    return includes


def symlink_python_files(dest):
    if dest == SRC_LOCATION:
        return

    for parent, dirs, files in os.walk(SRC_LOCATION):
        if os.path.basename(parent) == '__pycache__':
            continue

        def _is_python_file(f):
            return f.endswith('.py') and not f.endswith('_ext.py') \
                and not f.startswith('test_')

        files = [f for f in files if _is_python_file(f)]

        if not files:
            continue

        dest_parent = os.path.join(dest, *parent.split(os.sep)[1:])
        os.makedirs(dest_parent, exist_ok=True)
        for file in files:
            dst = os.path.join(dest_parent, file)
            src = os.path.relpath(os.path.join(parent, file), dest_parent)
            if os.path.exists(dst):
                os.unlink(dst)
            os.symlink(src, dst)


kits = {
    'platform': [
        'japronto.request.crequest', 'japronto.protocol.cprotocol',
        'japronto.protocol.creaper', 'japronto.router.cmatcher',
        'japronto.response.cresponse']
}


def get_parser():
    argparser = argparse.ArgumentParser('build')
    argparser.add_argument(
        '-d', dest='debug', const=True, action='store_const', default=False)
    argparser.add_argument(
        '--sanitize', dest='sanitize', const=True, action='store_const',
        default=False)
    argparser.add_argument(
        '--profile-generate', dest='profile_generate', const=True,
        action='store_const', default=False)
    argparser.add_argument('--dest', dest='dest', default='src')
    argparser.add_argument(
        '--profile-use', dest='profile_use', const=True,
        action='store_const', default=False)
    argparser.add_argument(
        '-flto', dest='flto', const=True,
        action='store_const', default=False)
    argparser.add_argument(
        '--profile-clean', dest='profile_clean', const=True,
        action='store_const', default=False)
    argparser.add_argument(
        '--disable-reaper', dest='enable_reaper', const=False,
        action='store_const', default=True)
    argparser.add_argument(
        '--disable-response-cache', dest='enable_response_cache', const=False,
        action='store_const', default=True)
    argparser.add_argument(
        '--coverage', dest='coverage', const=True,
        action='store_const', default=False)
    argparser.add_argument('-O1', dest='optimization', const='1',
                           action='store_const')
    argparser.add_argument('-O2', dest='optimization', const='2',
                           action='store_const')
    argparser.add_argument('-O3', dest='optimization', const='3',
                           action='store_const')
    argparser.add_argument('-Os', dest='optimization', const='s',
                           action='store_const')
    argparser.add_argument('-native', dest='native', const=True,
                           action='store_const', default=False)
    argparser.add_argument('--path', dest='path')
    argparser.add_argument('--extra-compile', dest='extra_compile', default='')
    argparser.add_argument('--kit', dest='kit')

    return argparser


def get_platform():
    argparser = get_parser()
    args = argparser.parse_args([])
    system = BuildSystem(args, relative_source=True)

    ext_modules = system.discover_extensions()
    ext_modules = [e for e in ext_modules if e.name in kits['platform']]

    print({e.name: e.sources for e in ext_modules})
    return ext_modules


class custom_build_ext(build_ext):
    def build_extensions(self):
        if self.compiler.compiler_type == 'unix':
            for ext in self.extensions:
                if not ext.extra_compile_args:
                    ext.extra_compiler_args = []
                extra_compile_args = ['-std=c99', '-UNDEBUG', '-D_GNU_SOURCE']
                if self.compiler.compiler_so[0].startswith('gcc') and sys.platform != 'darwin':
                    extra_compile_args.append('-frecord-gcc-switches')
                ext.extra_compile_args.extend(extra_compile_args)
        compile_c(
            self.compiler,
            'src/picohttpparser/picohttpparser.c',
            'src/picohttpparser/ssepicohttpparser.o',
            options={'unix': ['-msse4.2']})
        compile_c(
            self.compiler,
            'src/picohttpparser/picohttpparser.c',
            'src/picohttpparser/picohttpparser.o')
        build_ext.build_extensions(self)


def compile_c(compiler, cfile, ofile, *, options=None):
    if not options:
        options = {}

    options = options.get(compiler.compiler_type, [])
    cmd = [*compiler.compiler_so, *options, '-c', '-o', ofile, cfile]
    print("building '{}'".format(ofile))
    print(' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    argparser = get_parser()
    args = argparser.parse_args(sys.argv[1:])

    if args.profile_clean:
        profile_clean()
        return

    distutils.log.set_verbosity(1)

    system = BuildSystem(args)

    if args.path:
        ext_modules = [system.get_extension_by_path(args.path)]
    else:
        ext_modules = system.discover_extensions()

    if args.kit:
        ext_modules = [e for e in ext_modules if e.name in kits[args.kit]]

    def add_args(arg_name, values, append=True):
        for ext_module in ext_modules:
            arg_value = getattr(ext_module, arg_name) or []
            if append:
                arg_value.extend(values)
            else:
                newvalues = list(values)
                newvalues.extend(arg_value)
                arg_value = newvalues
            setattr(ext_module, arg_name, arg_value)

    def append_compile_args(*values):
        add_args('extra_compile_args', values)

    def append_link_args(*values):
        add_args('extra_link_args', values)

    def prepend_libraries(*values):
        add_args('libraries', values, append=False)

    if args.native:
        append_compile_args('-march=native')
    if args.optimization:
        append_compile_args('-O' + args.optimization)
    if args.debug:
        append_compile_args('-g3', '-O0', '-Wp,-U_FORTIFY_SOURCE')
    if args.sanitize:
        append_compile_args('-g3', '-fsanitize=address',
                            '-fsanitize=undefined', '-fno-common',
                            '-fno-omit-frame-pointer')
        prepend_libraries('asan', 'ubsan')
    if args.profile_generate:
        append_compile_args('--profile-generate')
        append_link_args('-lgcov')
    if args.profile_use:
        for ext_module in ext_modules:
            if ext_module.name in ('parser.cparser', 'pipeline.cpipeline'):
                continue
            ext_module.extra_compile_args.append('--profile-use')
    if args.flto:
        append_compile_args('-flto')
        append_link_args('-flto')
    if args.coverage:
        append_compile_args('--coverage')
        append_link_args('-lgcov')
    if args.extra_compile:
        append_compile_args(args.extra_compile)

    ext_modules = [e for e in ext_modules if system.should_rebuild(e)]
    if not ext_modules:
        return

    dist = Distribution(dict(ext_modules=ext_modules))

    prune(args.dest)

    cmd = custom_build_ext(dist)
    cmd.build_lib = os.path.join(args.dest, '.build/lib')
    cmd.build_temp = os.path.join(args.dest, '.build/temp')
    cmd.finalize_options()

    try:
        cmd.run()
    except CompileError:
        sys.exit(1)

    symlink_python_files(args.dest)

    for ext_module in ext_modules:
        os.makedirs(system.dest_folder(ext_module.name), exist_ok=True)
        shutil.copy(
            cmd.get_ext_fullpath(ext_module.name),
            system.dest_folder(ext_module.name))

    for ext_module in ext_modules:
        with open(system.build_toml(ext_module.name), 'w') as f:
            build_info = {
                'extra_compile_args': ext_module.extra_compile_args,
                'extra_link_args': ext_module.extra_link_args,
                'define_macros': dict(ext_module.define_macros),
                'sources': ext_module.sources
            }
            pytoml.dump(build_info, f)


if __name__ == '__main__':
    main()

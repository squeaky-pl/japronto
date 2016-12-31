import argparse
import distutils
from distutils.command.build_ext import build_ext, CompileError
from distutils.core import Distribution
from glob import glob
import os.path
import shutil
from importlib import import_module
import sysconfig
import os
import sys
import pytoml


SRC_LOCATION = 'src'
sys.path.insert(0, SRC_LOCATION)


class BuildSystem:
    def __init__(self, args):
        self.args = args
        self.dest = self.args.dest

    def get_extension_by_path(self, path):
        path = SRC_LOCATION + '/' + path
        module_import = os.path.relpath(os.path.splitext(path)[0], SRC_LOCATION) \
            .replace('/', '.')
        module = import_module(module_import)
        module.system = self
        extension = module.get_extension()

        base_path = os.path.dirname(path)

        def fix_path(p):
            if os.path.isabs(p):
                return p

            return os.path.abspath(os.path.join(base_path, p))

        for attr in ['sources', 'include_dirs', 'library_dirs', 'runtime_library_dirs']:
            val = getattr(extension, attr)
            if not val:
                continue

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
        return self.dest +  '/' + '/'.join(mod_name.split('.')) + '.build.toml'

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
            "extra_link_args": ext.extra_link_args}

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


def prune():
    paths = glob('build/**/*.o', recursive=True)
    paths.extend(glob('build/**/*.so', recursive=True))
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

        files = [
            f for f in files
            if f.endswith('.py') and not f.endswith('_ext.py')
            and not f.startswith('test_')]

        if not files:
            continue

        dest_parent = os.path.join(dest, *os.path.split(parent)[1:])
        os.makedirs(dest_parent, exist_ok=True)
        for file in files:
            dst = os.path.join(dest_parent, file)
            src = os.path.relpath(os.path.join(parent, file), dest_parent)
            if os.path.exists(dst):
                os.unlink(dst)
            os.symlink(src, dst)


def main():
    argparser = argparse.ArgumentParser('build')
    argparser.add_argument(
        '-d', dest='debug', const=True, action='store_const', default=False)
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
        '--coverage', dest='coverage', const=True,
        action='store_const', default=False)
    argparser.add_argument('--path', dest='path')
    argparser.add_argument('--extra-compile', dest='extra_compile', default='')
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

    def append_args(arg_name, values):
        for ext_module in ext_modules:
            arg_value = getattr(ext_module, arg_name) or []
            arg_value.extend(values)
            setattr(ext_module, arg_name, arg_value)

    def append_compile_args(*values):
        append_args('extra_compile_args', values)

    def append_link_args(*values):
        append_args('extra_link_args', values)


    append_compile_args('-frecord-gcc-switches', '-UNDEBUG')

    if args.debug:
        append_compile_args('-g3', '-O0', '-Wp,-U_FORTIFY_SOURCE')
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

    prune()

    cmd = build_ext(dist)
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
                'extra_link_args': ext_module.extra_link_args
            }
            pytoml.dump(f, build_info)

if __name__ == '__main__':
    main()

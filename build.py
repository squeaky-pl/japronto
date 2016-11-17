import distutils
from distutils.command.build_ext import build_ext
from distutils.core import Distribution
from glob import glob
import os.path
import shutil
from importlib import import_module

ext_dirs = ['parser']


def discover_extensions():
    extensions = []

    for directory in ext_dirs:
        ext_files = glob(os.path.join(directory, '*_ext.py'))
        for f in ext_files:
            print('Collected: ', f)
        ext_modules = [os.path.splitext(f)[0].replace('/', '.') for f in ext_files]
        dir_extensions = [import_module(m).get_extension() for m in ext_modules]
        for e in dir_extensions:
            e.origin_dir = directory
        extensions.extend(dir_extensions)

    return extensions


def main():
    distutils.log.set_verbosity(1)

    ext_modules = discover_extensions()
    dist = Distribution(dict(ext_modules=ext_modules))

    shutil.rmtree('build')

    cmd = build_ext(dist)
    cmd.finalize_options()
    cmd.run()

    for ext_module in ext_modules:
        shutil.copy(
            cmd.get_ext_fullpath(ext_module.name), ext_module.origin_dir)


if __name__ == '__main__':
    main()

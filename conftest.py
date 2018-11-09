import subprocess
import sys
import os
import shutil


builds = []
coverages = set()


def add_build(mark):
    global builds
    args, kwargs = list(mark.args), mark.kwargs.copy()
    kwargs.pop('coverage', None)
    cfg = args, kwargs
    if cfg not in builds:
        builds.append(cfg)


def execute_builds():
    common_options = ['--coverage', '-d', '--sanitize']
    for args, kwargs in builds:
        build_options = args[:]
        build_options.extend(['--dest', kwargs.get('dest', '.test')])
        if 'kit' not in kwargs:
            build_options.extend(['--kit', 'platform'])
        build_options.extend(common_options)

        print('Executing build', *build_options)
        subprocess.check_call([sys.executable, 'build.py', *build_options])


def add_coverage(mark):
    dest = mark.kwargs.get('dest', '.test')
    coverages.add(dest)


def setup_coverage():
    if coverages:
        print('Setting up C coverage for', *coverages)

    for dest in coverages:
        subprocess.check_call([
             'lcov', '--base-directory', '.', '--directory',
             dest + '/.build/temp', '--zerocounters', '-q'])


def make_coverage():
    for dest in coverages:
        try:
            os.unlink(dest + '/coverage.info')
        except FileNotFoundError:
            pass

        subprocess.check_call([
            'lcov', '--base-directory', '.', '--directory',
            dest + '/.build/temp', '-c', '-o', dest + '/coverage.info', '-q'])
        subprocess.check_call([
            'lcov', '--remove', dest + '/coverage.info',
            '/usr*', '-o', 'coverage.info', '-q'])

        try:
            shutil.rmtree(dest + '/coverage_report')
        except FileNotFoundError:
            pass

        subprocess.check_call([
            'genhtml', '-o', dest + '/coverage_report',
            dest + '/coverage.info', '-q'
        ])

        print('C coverage report saved in',
              dest + '/coverage_report/index.html')


def pytest_itemcollected(item):
    needs_build = item.get_closest_marker('needs_build')
    if needs_build:
        add_build(needs_build)
    if needs_build and needs_build.kwargs.get('coverage'):
        add_coverage(needs_build)


def pytest_collection_modifyitems(config, items):
    execute_builds()
    setup_coverage()


def pytest_unconfigure():
    make_coverage()

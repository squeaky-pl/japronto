import subprocess
import sys
import os
import shutil
import pytest


builds = []

def add_build(options):
    global builds
    if not options in builds:
        builds.append(options)

def execute_builds():
    common_options = ['--coverage', '-d', '--sanitize']
    for build_options in builds:
        build_options = list(build_options)
        if '--dest' not in build_options:
            build_options.extend(['--dest', '.test'])
        build_options.extend(common_options)

        print('Executing build', *build_options)
        subprocess.check_call([sys.executable, 'build.py', *build_options])


def pytest_itemcollected(item):
    needs_build = item.get_marker('needs_build')
    if needs_build:
        add_build(needs_build.args)


def pytest_collection_modifyitems(config, items):
    execute_builds()



#@pytest.fixture(scope='session', autouse=True)
def global_fixture():
    os.putenv('PYTHONPATH', '.test')
    sys.path.insert(0, '.test')
    subprocess.check_call([
        sys.executable, 'build.py', '--coverage',
        '--dest', '.test', '-d', '--sanitize'])

    subprocess.check_call([
        'lcov', '--base-directory', '.', '--directory',
        '.test/.build/temp', '--zerocounters', '-q'])

    yield

    try:
        os.unlink('coverage.info')
    except FileNotFoundError:
        pass

    subprocess.check_call([
        'lcov', '--base-directory', '.', '--directory',
        '.test/.build/temp', '-c', '-o', 'coverage.info', '-q'])
    subprocess.check_call([
        'lcov', '--remove', 'coverage.info',
        '/usr*', '-o', 'coverage.info', '-q'])

    try:
        shutil.rmtree('test_coverage')
    except FileNotFoundError:
        pass

    subprocess.check_call([
        'genhtml', '-o', 'test_coverage', 'coverage.info', '-q'
    ])

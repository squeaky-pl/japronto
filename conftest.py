import subprocess
import sys
import os
import shutil
import pytest


@pytest.fixture(scope='session', autouse=True)
def global_fixture():
    os.putenv('PYTHONPATH', '.test')
    sys.path.insert(0, '.test')
    subprocess.check_call([
        sys.executable, 'build.py', '--coverage', '--dest', '.test'])

    subprocess.check_call([
        'lcov', '--base-directory', '.', '--directory',
        'build/temp.linux-x86_64-3.5', '--zerocounters', '-q'])

    yield

    try:
        os.unlink('coverage.info')
    except FileNotFoundError:
        pass

    subprocess.check_call([
        'lcov', '--base-directory', '.', '--directory',
        'build/temp.linux-x86_64-3.5', '-c', '-o', 'coverage.info', '-q'])
    subprocess.check_call([
        'lcov', '--remove', 'coverage.info',
        '/usr*', '-o', 'coverage.info', '-q'])

    shutil.rmtree('test_coverage')

    subprocess.check_call([
        'genhtml', '-o', 'test_coverage', 'coverage.info', '-q'
    ])

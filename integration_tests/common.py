import os
import subprocess
import ctypes.util
import sys


def start_server(script, *, stdout=None, path=None):
    if not isinstance(script, list):
        script = [script]
    if path:
        os.putenv('PYTHONPATH', path)
    os.putenv('LD_PRELOAD', ctypes.util.find_library('asan'))
    os.putenv('LSAN_OPTIONS', 'suppressions=suppr.txt')
    server = subprocess.Popen([sys.executable, *script], stdout=stdout)
    os.unsetenv('LSAN_OPTIONS')
    os.unsetenv('LD_PRELOAD')
    if path:
        os.unsetenv('PYTHONPATH')

    return server

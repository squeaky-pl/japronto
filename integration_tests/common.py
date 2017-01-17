import os
import subprocess
import ctypes.util
import sys
import time

import psutil


def start_server(script, *, stdout=None, path=None, sanitize=True, wait=True):
    if not isinstance(script, list):
        script = [script]
    if path:
        os.putenv('PYTHONPATH', path)
    if sanitize:
        os.putenv('LD_PRELOAD', ctypes.util.find_library('asan'))
        os.putenv('LSAN_OPTIONS', 'suppressions=suppr.txt')
    server = subprocess.Popen([sys.executable, *script], stdout=stdout)
    if sanitize:
        os.unsetenv('LSAN_OPTIONS')
        os.unsetenv('LD_PRELOAD')
    if path:
        os.unsetenv('PYTHONPATH')

    if wait:
        proc = psutil.Process(server.pid)

        # wait until the server socket is open
        while 1:
            assert server.poll() is None
            if proc.connections():
                break
            time.sleep(.001)

    assert server.poll() is None

    return server

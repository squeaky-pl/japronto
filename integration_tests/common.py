import os
import subprocess
import ctypes.util
import sys
import time

import psutil


def start_server(script, *, stdout=None, path=None, sanitize=True, wait=True,
                 return_process=False, buffer=False):
    if not isinstance(script, list):
        script = [script]
    if path:
        os.putenv('PYTHONPATH', path)
    if sanitize:
        os.putenv('LD_PRELOAD', ctypes.util.find_library('asan'))
        os.putenv('LSAN_OPTIONS', 'suppressions=suppr.txt')
    if not buffer:
        os.putenv('PYTHONUNBUFFERED', '1')
    server = subprocess.Popen([sys.executable, *script], stdout=stdout)
    if not buffer:
        os.unsetenv('PYTHONUNBUFFERED')
    if sanitize:
        os.unsetenv('LSAN_OPTIONS')
        os.unsetenv('LD_PRELOAD')
    if path:
        os.unsetenv('PYTHONPATH')

    process = psutil.Process(server.pid)
    if wait:
        # wait until the server socket is open
        while 1:
            assert server.poll() is None
            conn_num = len(process.connections())
            for child in process.children():
                conn_num += len(child.connections())
            if conn_num:
                break
            time.sleep(.001)

    assert server.poll() is None

    if return_process:
        return server, process
    else:
        return server

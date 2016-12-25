import subprocess
import sys
import sysconfig

import psutil
import pytest
import time
from elftools.elf.elffile import ELFFile

import client


@pytest.fixture(scope='function')
def server(request):
    pytest.set_trace()

    cprotocol_so = 'protocol/cprotocol.{}.so' \
        .format(sysconfig.get_config_var('SOABI'))

    with open(cprotocol_so, 'rb') as f:
        elf = ELFFile(f)
        command_line = elf.get_section_by_name('.GCC.command.line').data() \
            .split(b'\x00')

    if b'-D PROTOCOL_TRACK_REFCNT=1' not in command_line:
        subprocess.check_call([
            sys.executable, 'build.py',
            '--extra-compile=-DPROTOCOL_TRACK_REFCNT=1'])

    arg = request.node.get_marker('arg').args[0]
    server = subprocess.Popen([
        sys.executable, 'integration_tests/noleak.py', arg])
    proc = psutil.Process(server.pid)

    # wait until the server socket is open
    while 1:
        if proc.connections():
            break
        time.sleep(.001)

    yield server

    server.terminate()
    server.wait()
    assert server.returncode == 0


@pytest.fixture(scope='function')
def connection(server):
    conn = client.Connection('localhost:8080')
    yield conn
    conn.close()


@pytest.mark.arg('method')
def test_method(connection):
    methods = ['GET', 'POST', 'PATCH', 'DELETE', 'PUT']

    for method in methods:
        connection.putrequest(method, '/noleak/1/2')
        connection.endheaders()

        response = connection.getresponse()
        assert response.status == 200

import pytest
import subprocess
import sys
import urllib3.connection
import socket
import psutil
import time
import json
import urllib.parse
import string
from hypothesis import given, strategies as st, settings, Verbosity


@pytest.fixture(autouse=True)
def server():
    server = subprocess.Popen([sys.executable, 'integration_tests/dump.py'])
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


def connect():
    return urllib3.connection.HTTPConnection('localhost:8080')


method_alphabet = string.digits + string.ascii_letters + string.punctuation
@given(method=st.text(method_alphabet, min_size=1))
@settings(verbosity=Verbosity.verbose)
def test_method(method):
    connection = connect()
    connection.request(method, '/dump/1/2')
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['method'] == method

    connection.close()


param_alphabet = st.characters(blacklist_characters='/?') \
    .filter(lambda x: not any(0xD800 <= ord(c) <= 0xDFFF for c in x))
param = st.text(param_alphabet, min_size=1)
@given(param1=param, param2=param)
@settings(verbosity=Verbosity.verbose)
def test_match_dict(param1, param2):
    connection = connect()
    connection.request('GET', urllib.parse.quote('/dump/{}/{}'.format(param1, param2)))
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))

    assert response.status == 200
    assert json_body['match_dict'] == {'p1': param1, 'p2': param2}

    connection.close()

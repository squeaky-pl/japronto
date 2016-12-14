import pytest
import subprocess
import sys
import urllib3.connection
import socket
import psutil
import time
import json


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


@pytest.fixture
def connection():
    return urllib3.connection.HTTPConnection('localhost:8080')


def test(connection):
    connection.request('GET', '/dump/1/2')
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))
    print(json_body)

    connection.request('GET', '/dump/3/4')
    response = connection.getresponse()
    json_body = json.loads(response.read().decode('utf-8'))
    print(json_body)

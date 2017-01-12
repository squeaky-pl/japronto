import os.path
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../src'))

from app import Application


def extended_hello(request):
    if request.host_startswith('api.'):
        text = 'Hello ' + request.reversed_agent
    else:
        text = 'Hello stranger'

    return request.Response(text=text)


def reversed_agent(request):
    return request.headers['User-Agent'][::-1]


def host_startswith(request, prefix):
    return request.headers['Host'].startswith(prefix)


app = Application()
app.extend_request(reversed_agent, property=True)
app.extend_request(host_startswith)

r = app.router
r.add_route('/', extended_hello)


app.serve()

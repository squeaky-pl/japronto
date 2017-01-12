import os.path
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../src'))

from app import Application


def extended_hello(request):
    return request.Response(text='Hello ' + request.reversed_agent)


def reversed_agent(request):
    return request.headers['User-Agent'][::-1]


app = Application()
app.extend_request(reversed_agent, property=True)

r = app.router
r.add_route('/', extended_hello)


app.serve()

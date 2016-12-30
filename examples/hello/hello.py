import os.path
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../src'))

from app import Application


def hello(request):
    return request.Response(text='Hello world!')


app = Application()

r = app.get_router()
r.add_route('/', hello)

app.serve()

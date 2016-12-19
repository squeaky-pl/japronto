import os.path
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import Application


def dump(request):
    result = {
        "method": request.method,
        "path": request.path,
        "query_string": request.query_string,
        "headers": request.headers,
        "match_dict": request.match_dict
    }

    return request.Response(json=result)


def dump_body(request):
    return request.Response(body=request.body)


app = Application()

r = app.get_router()
r.add_route('/dump/{p1}/{p2}', dump)
r.add_route('/dump/body', dump_body)


if __name__ == '__main__':
    app.serve()

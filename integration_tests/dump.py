import os.path
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import Application


def dump(request):
    result = {
        "method": request.method,
        "path": request.path,
        "query_string": request.query_string,
        "query": request.query,
        "headers": request.headers,
        "match_dict": request.match_dict,
        "mime_type": request.mime_type,
        "encoding": request.encoding,
        "keep_alive": request.keep_alive,
        "form": request.form
    }

    return request.Response(json=result)


app = Application()

r = app.get_router()
r.add_route('/dump/{p1}/{p2}', dump)


if __name__ == '__main__':
    app.serve()

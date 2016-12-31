import os.path
import sys
import base64


from app import Application


def dump(request):
    body = request.body
    if body is not None:
        body = base64.b64encode(body).decode('ascii')

    result = {
        "method": request.method,
        "path": request.path,
        "query_string": request.query_string,
        "headers": request.headers,
        "match_dict": request.match_dict,
        "body": body
    }

    return request.Response(json=result)

app = Application()

r = app.get_router()
r.add_route('/dump/{p1}/{p2}', dump)


if __name__ == '__main__':
    app.serve()

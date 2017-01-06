import os.path
import sys
import base64
import asyncio


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
        "body": body,
        "route": request.route.pattern
    }

    return request.Response(json=result)


async def adump(request):
    sleep = float(request.query.get('sleep', 0))
    await asyncio.sleep(sleep)

    return dump(request)


app = Application()

r = app.get_router()
r.add_route('/dump/{p1}/{p2}', dump)
r.add_route('/dump1/{p1}/{p2}', dump)
r.add_route('/dump2/{p1}/{p2}', dump)
r.add_route('/adump/{p1}/{p2}', adump)


if __name__ == '__main__':
    app.serve()

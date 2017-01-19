import os.path
import sys
import base64
import asyncio


from japronto.app import Application

class ForcedException(Exception):
    pass


def dump(request, exception=None):
    if not exception and 'Force-Raise' in request.headers:
        raise ForcedException(request.headers['Force-Raise'])

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
        "route": request.route and request.route.pattern
    }

    if exception:
         result['exception'] = {
             "type": type(exception).__name__,
             "args": ", ".join(str(a) for a in exception.args)
         }

    return request.Response(status_code=500 if exception else 200, json=result)


async def adump(request):
    sleep = float(request.query.get('sleep', 0))
    await asyncio.sleep(sleep)

    return dump(request)


app = Application()

r = app.router
r.add_route('/dump/{p1}/{p2}', dump)
r.add_route('/dump1/{p1}/{p2}', dump)
r.add_route('/dump2/{p1}/{p2}', dump)
r.add_route('/async/dump/{p1}/{p2}', adump)
r.add_route('/async/dump1/{p1}/{p2}', adump)
r.add_route('/async/dump2/{p1}/{p2}', adump)
app.add_error_handler(None, dump)


if __name__ == '__main__':
    app.run()

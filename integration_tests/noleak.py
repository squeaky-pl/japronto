import os.path
import sys
import base64


from app import Application


prop = sys.argv[1]

if prop == 'method':
    def noleak(request):
        return request.Response(text=request.method)
elif prop == 'path':
    def noleak(request):
        return request.Response(text=request.path)
elif prop == 'match_dict':
    def noleak(request):
        return request.Response(json=request.match_dict)
elif prop == 'query_string':
    def noleak(request):
        return request.Response(text=request.query_string)
elif prop == 'headers':
    def noleak(request):
        return request.Response(json=request.headers)
elif prop == 'body':
    def noleak(request):
        return request.Response(body=request.body)
elif prop == 'keep_alive':
    def noleak(request):
        return request.Response(text=str(request.keep_alive))
elif prop == 'route':
    def noleak(request):
        return request.Response(text=str(request.route))

app = Application()

r = app.router
r.add_route('/noleak/{p1}/{p2}', noleak)


if __name__ == '__main__':
    app.serve()

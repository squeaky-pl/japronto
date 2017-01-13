from app import Application

def dump(request):
    text = """
Method: {0.method}
Path: {0.path}
Version: {0.version}
Headers: {0.headers}
Match: {0.match_dict}
Body: {0.body}
QS: {0.query_string}
query: {0.query}
mime_type: {0.mime_type}
encoding: {0.encoding}
form: {0.form}
keep_alive: {0.keep_alive}
route: {0.route}
hostname: {0.hostname}
port: {0.port}
remote_addr: {0.remote_addr}
""".strip().format(request)

    return request.Response(text=text)


if __name__ == '__main__':
    app = Application()
    app.router.add_route('/', dump)
    app.router.add_route('/{a}/{b}', dump)

    app.serve()

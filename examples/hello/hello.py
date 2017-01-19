from japronto.app import Application


def hello(request):
    return request.Response(text='Hello world!')


app = Application()

r = app.router
r.add_route('/', hello)

app.run()

from japronto import Application


def slash(request):
    return request.Response(text='Hello {} /!'.format(request.method))


def get_love(request):
    return request.Response(text='Got some love')


def methods(request):
    return request.Response(text=request.method)


def params(request):
    return request.Response(text=str(request.match_dict))


app = Application()

r = app.router
r.add_route('/', slash)
r.add_route('/love', get_love, 'GET')
r.add_route('/methods', methods, methods=['POST', 'DELETE'])
r.add_route('/params/{p1}/{p2}', params)

app.run()

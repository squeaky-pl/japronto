from japronto import Application


def extended_hello(request):
    if request.host_startswith('api.'):
        text = 'Hello ' + request.reversed_agent
    else:
        text = 'Hello stranger'

    return request.Response(text=text)


def with_callback(request):
    def cb(r):
        print('Done!')

    request.add_done_callback(cb)

    return request.Response(text='cb')


def reversed_agent(request):
    return request.headers['User-Agent'][::-1]


def host_startswith(request, prefix):
    return request.headers['Host'].startswith(prefix)


app = Application()
app.extend_request(reversed_agent, property=True)
app.extend_request(host_startswith)

r = app.router
r.add_route('/', extended_hello)
r.add_route('/callback', with_callback)


app.run()

from japronto import Application, RouteNotFoundException


class KittyError(Exception):
    def __init__(self):
        self.greet = 'meow'

class DoggieError(Exception):
    def __init__(self):
        self.greet = 'woof'


def cat(request):
    raise KittyError()


def dog(request):
    raise DoggieError()


def unhandled(request):
    1 / 0


app = Application()

r = app.router
r.add_route('/cat', cat)
r.add_route('/dog', dog)
r.add_route('/unhandled', unhandled)


def handle_cat(request, exception):
    return request.Response(text='Just a kitty, ' + exception.greet)


def handle_dog(request, exception):
    return request.Response(text='Just a doggie, ' + exception.greet)


def handle_not_found(request, exception):
    return request.Response(code=404, text="Are you lost, pal?")


app.add_error_handler(KittyError, handle_cat)
app.add_error_handler(DoggieError, handle_dog)
app.add_error_handler(RouteNotFoundException, handle_not_found)

app.run()

class Route:
    def __init__(self, pattern, handler, methods):
        self.pattern = pattern
        self.handler = handler
        self.methods = methods

    def __repr__(self):
        return '<Route {}, {}>'.format(self.pattern, self.methods)


class Matcher:
    def __init__(self, router):
        self.router = router

        #compile

    def match_request(self, request):
        for r in self.router._routes:
            if request.path == r.pattern and request.method in r.methods:
                return r

class Router:
    def __init__(self, matcher_factory=Matcher):
        self._routes = []
        self.matcher_factory = matcher_factory

    def add_route(self, pattern, handler, method=None, methods=None):
        assert not(method and methods), "Cannot use method and methods"

        if method:
            methods = [method]

        if not methods:
            methods = []

        methods = [m.upper() for m in methods]
        route = Route(pattern, handler, methods)

        self._routes.append(route)

        return route

    def get_matcher(self):
        return self.matcher_factory(self)

from .route import Route, RouteNotFoundException
from .cmatcher import Matcher


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

        methods = {m.upper() for m in methods}
        route = Route(pattern, handler, methods)

        self._routes.append(route)

        return route

    def get_matcher(self):
        return self.matcher_factory(self._routes)

class Matcher:
    def __init__(self, routes):
        self._routes = routes

    def match_request(self, request):
        for route in self._routes:
            match_dict = {}
            rest = request.path

            value = True
            for typ, data in route.segments:
                if typ == 'exact':
                    if not rest.startswith(data):
                        break

                    rest = rest[len(data):]
                elif typ == 'placeholder':
                    value, slash, rest = rest.partition('/')
                    if not value:
                        break
                    match_dict[data] = value
                    rest = slash + rest
                else:
                    assert 0, 'Unknown type'

            if rest:
                continue

            if not value:
                continue

            if len(match_dict) != route.placeholder_cnt:
                continue

            if route.methods and request.method not in route.methods:
                continue

            return route, match_dict

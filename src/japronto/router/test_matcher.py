from functools import partial

import pytest

from . import Route
from .matcher import Matcher
from .cmatcher import Matcher as CMatcher


class FakeRequest:
    def __init__(self, method, path):
        self.method = method
        self.path = path

    @classmethod
    def from_str(cls, value):
        return cls(*value.split())


class TracingRoute(Route):
    cnt = 0

    def __new__(cls, *args, **kw):
        print('new', args)
        cls.cnt += 1
        return Route.__new__(cls)

    def __init__(self, pattern, methods):
        super().__init__(pattern, lambda x: None, methods=methods)

    def __del__(self):
        type(self).cnt -= 1
        print('del')


def route_from_str(value):
    pattern, *methods = value.split()
    if methods:
        methods = methods[0].split(',')

    return TracingRoute(pattern, methods=methods)


def parametrize_make_matcher():
    def make(cls):
        routes = [route_from_str(r) for r in [
            '/',
            '/test GET',
            '/hi/{there} POST,DELETE',
            '/{oh}/{dear} PATCH',
            '/lets PATCH'
        ]]

        return cls(routes)

    make_matcher = partial(make, Matcher)
    make_cmatcher = partial(make, CMatcher)

    return pytest.mark.parametrize(
        'make_matcher', [make_matcher, make_cmatcher], ids=['py', 'c'])


def parametrize_request_route_and_dict(cases):
    return pytest.mark.parametrize(
        'req,route,match_dict',
        ((FakeRequest.from_str(req), route_from_str(route), match_dict)
            for req, route, match_dict in cases),
        ids=[req + '-' + route for req, route, _ in cases])


@parametrize_request_route_and_dict([
    ('GET /', '/', {}),
    ('POST /', '/', {}),
    ('GET /test', '/test GET', {}),
    ('DELETE /hi/jane', '/hi/{there} POST,DELETE', {'there': 'jane'}),
    ('PATCH /lets/go', '/{oh}/{dear} PATCH', {'oh': 'lets', 'dear': 'go'}),
    ('PATCH /lets', '/lets PATCH', {})
])
@parametrize_make_matcher()
def test_matcher(make_matcher, req, route, match_dict):
    cnt = TracingRoute.cnt

    matcher = make_matcher()
    assert matcher.match_request(req) == (route, match_dict)
    del matcher

    assert cnt == TracingRoute.cnt


def parametrize_request(requests):
    return pytest.mark.parametrize(
        'req', (FakeRequest.from_str(r) for r in requests), ids=requests)


@parametrize_request([
    'POST /test',
    'GET /test/',
    'GET /hi/jane',
    'POST /hi/jane/',
    'POST /hi/',
    'GET /abc',
    'PATCH //dance'
])
@parametrize_make_matcher()
def test_matcher_not_found(make_matcher, req):
    cnt = TracingRoute.cnt

    matcher = make_matcher()
    assert matcher.match_request(req) is None
    del matcher

    assert cnt == TracingRoute.cnt

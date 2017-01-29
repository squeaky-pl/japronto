import asyncio
from collections import namedtuple

import pytest

from .route import parse, MatcherEntry, Segment, SegmentType, Route, \
    compile, roundto8


@pytest.mark.parametrize('pattern,result', [
    ('/', [('exact', '/')]),
    ('/{{a}}', [('exact', '/{a}')]),
    ('{a}', [('placeholder', 'a')]),
    ('a/{a}', [('exact', 'a/'), ('placeholder', 'a')]),
    ('{a}/a', [('placeholder', 'a'), ('exact', '/a')]),
    ('{a}/{{a}}', [('placeholder', 'a'), ('exact', '/{a}')]),
    ('{a}/{b}', [('placeholder', 'a'), ('exact', '/'), ('placeholder', 'b')])
])
def test_parse(pattern, result):
    assert parse(pattern) == result


@pytest.mark.parametrize('pattern,error', [
    ('{a', 'Unbalanced'),
    ('{a}/{b', 'Unbalanced'),
    ('{a}a', 'followed by'),
    ('{a}/{a}', 'Duplicate')
])
def test_parse_error(pattern, error):
    with pytest.raises(ValueError) as info:
        parse(pattern)
    assert error in info.value.args[0]


DecodedRoute = namedtuple(
    'DecodedRoute',
    'route_id,handler_id,coro_func,simple,placeholder_cnt,segments,methods')


def decompile(buffer):
    route_id, handler_id, coro_func, simple, \
        pattern_len, methods_len, placeholder_cnt \
        = MatcherEntry.unpack_from(buffer, 0)
    offset = MatcherEntry.size
    pattern_offset_end = offset + roundto8(pattern_len)

    segments = []
    while offset < pattern_offset_end:
        typ, segment_length = Segment.unpack_from(buffer, offset)
        offset += Segment.size
        typ = SegmentType(typ).name.lower()
        data = buffer[offset:offset + segment_length].decode('utf-8')
        offset += roundto8(segment_length)

        segments.append((typ, data))

    methods = buffer[offset:offset + methods_len].strip().decode('ascii') \
        .split()

    return DecodedRoute(
        route_id, handler_id, coro_func, simple,
        placeholder_cnt, segments, methods)


def handler():
    pass


async def coro():
    # needs to have await to prevent being promoted to function
    await asyncio.sleep(1)


@pytest.mark.parametrize('route', [
    Route('/', handler, []),
    Route('/', coro, ['GET']),
    Route('/test/{hi}', handler, []),
    Route('/test/{hi}', coro, ['POST']),
    Route('/tést', coro, ['POST'])
], ids=Route.describe)
def test_compile(route):
    decompiled = decompile(compile(route))

    assert decompiled.route_id == id(route)
    assert decompiled.handler_id == id(route.handler)
    assert decompiled.coro_func == asyncio.iscoroutinefunction(route.handler)
    assert not decompiled.simple
    assert decompiled.placeholder_cnt == route.placeholder_cnt
    assert decompiled.segments == route.segments
    assert decompiled.methods == route.methods

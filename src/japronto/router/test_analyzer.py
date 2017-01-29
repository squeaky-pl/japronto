from collections import OrderedDict

import pytest

from . import analyzer


simple_fixtures = OrderedDict([
    ('empty', ('def a(): pass', False)),
    ('arg', ('def a(b): return b', False)),
    ('simple', ('def a(c): return c.Response()', True)),
    ('body', ('def a(c): return c.Response(body="abc")', True)),
    ('wrongattr', ('def a(d): return d.R()', False)),
    ('extracall', (
        '''
def a(b):
    d()
    return b.Response()

def d():
    pass
        ''', False)),
    ('expressions', (
        '''
def a(b):
    c = "Hey!"
    d = "Dude"
    return b.Response(json={c: d})
        ''', True))
])


@pytest.mark.parametrize(
    'code,simple', simple_fixtures.values(), ids=list(simple_fixtures.keys()))
def test_is_simple(code, simple):
    module = compile(code, '?', 'exec')
    fun_code = module.co_consts[0]

    assert analyzer.is_simple(fun_code) == simple


pointless_fixtures = OrderedDict([
    ('empty', ('async def a(): pass', True)),
    ('simple', ('async def a(): return 1', True)),
    ('yieldfrom', ('def a(b): yield from b', False)),
    ('await', ('async def a(b): await b', False))
])


@pytest.mark.parametrize(
    'code,pointless', pointless_fixtures.values(),
    ids=list(pointless_fixtures.keys()))
def test_is_pointless(code, pointless):
    module = compile(code, '?', 'exec')
    fun_code = module.co_consts[0]

    assert analyzer.is_pointless_coroutine(fun_code) == pointless

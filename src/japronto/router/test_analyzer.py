from collections import OrderedDict

import pytest

from . import analyzer


fixtures = OrderedDict([
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
params = fixtures.values()
ids = list(fixtures.keys())


@pytest.mark.parametrize('code,simple', params, ids=ids)
def test_analyzer(code, simple):
    module = compile(code, '?', 'exec')
    fun_code = module.co_consts[0]

    assert analyzer.is_simple(fun_code) == simple

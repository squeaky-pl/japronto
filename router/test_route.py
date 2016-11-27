import pytest

from router.route import parse


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

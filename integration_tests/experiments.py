import pytest


@pytest.fixture(autouse=True)
def my_fix(request):
    print('auto')
    pytest.set_trace()


@pytest.fixture(params=[1, 2])
def size_k(request):
    return request.param

# @pytest.fixture(autouse=True, scope='module')
# def a():
#     print('a')


# @pytest.fixture(scope='function', params=[1,2])
# def fix():
#     print('> fix')
#     yield 3
#     print('< fix')


# def test(my_fix):
#     print(test)

def test1(size_k):
    print(test1)

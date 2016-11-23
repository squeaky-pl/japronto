import asyncio
import gc
import sys
from collections import namedtuple

import pytest

from pipeline import Pipeline
from pipeline.cpipeline import Pipeline as CPipeline


Example = namedtuple('Example', 'value')


class FakeLoop:
    def call_soon(self, callback, val):
        callback(val)

    def get_debug(self):
        return False

    def create_future(self):
        return asyncio.Future(loop=self)


class FakeFuture:
    cnt = 0

    def __new__(cls):
        print('new')
        cls.cnt += 1
        return object.__new__(cls)

    def __del__(self):
        type(self).cnt -= 1
        print('del')

    def __init__(self):
        self.callbacks = []

    def add_done_callback(self, cb):
        self.callbacks.append(cb)

    def done(self):
        return hasattr(self, '_result')

    def result(self):
        return self._result

    def set_result(self, result):
        self._result = result

        for cb in self.callbacks:
            cb(self)

        self.callbacks = []


def parametrize_make_pipeline():
    return pytest.mark.parametrize('make_pipeline', [CPipeline, Pipeline],
        ids=['c', 'py'])


def parametrize_case(examples):
    cases = [parse_case(i) for i in examples]

    return pytest.mark.parametrize('case', cases, ids=examples)


def parse_case(case):
    return [Example(int(c)) for c in case.split('+')]


def create_futures(resolves, case):
    futures = [None] * len(case)
    case = case[:]
    for c in sorted(case):
        idx = case.index(c)
        futures[idx] = resolves[idx]()
        case[idx] = None

    return tuple(futures)


@parametrize_case([
    '1',
    '1+5', '5+1',
    '1+5+10', '10+5+1', '5+1+10', '10+1+5',
    '1+10+5+1'
])
@parametrize_make_pipeline()
def test(make_pipeline, case):
    pipeline = make_pipeline()
    def queue(x):
        fut = FakeFuture()
        pipeline.queue(fut)

        def resolve():
            fut.set_result(x)
            return fut

        return resolve

    resolves = tuple(queue(v) for v in case)
    futures = create_futures(resolves, case)

    assert pipeline.tail is None

    del resolves

    # this loop is not pythonic on purpose
    # carefully don't create extra references
    for i in range(len(futures)):
        print(sys.getrefcount(futures[i]))
    del i

    assert pipeline.results == case

    gc.collect()

    del futures

    gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()

    print(gc.garbage)
    gc.set_debug(0)

    assert FakeFuture.cnt == 0

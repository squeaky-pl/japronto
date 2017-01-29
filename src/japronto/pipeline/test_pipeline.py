import asyncio
import gc
import sys
from collections import namedtuple
from functools import partial

import pytest
import uvloop

from japronto.pipeline import Pipeline
from japronto.pipeline.cpipeline import Pipeline as CPipeline


Example = namedtuple('Example', 'value,delay')


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
    def make_pipeline(cls):
        results = []

        def append(task):
            results.append(task.result())

        return cls(append), results

    return pytest.mark.parametrize(
        'make_pipeline',
        [partial(make_pipeline, CPipeline), partial(make_pipeline, Pipeline)],
        ids=['c', 'py'])


def parametrize_case(examples):
    cases = [parse_case(i) for i in examples]

    return pytest.mark.parametrize('case', cases, ids=examples)


def parse_example(e, accum):
    value, delay = map(int, e.split('@')) if '@' in e else (int(e), 0)

    return Example(value, delay + accum)


def parse_case(case):
    results = []
    delay = 0
    for c in case.split('+'):
        e = parse_example(c, delay)
        results.append(e)
        delay = e.delay

    return results


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
    '1+10+5+1', '1+1+10+5', '10+5+1+1', '1+1+5+10'
])
@parametrize_make_pipeline()
def test_fake_future(make_pipeline, case):
    pipeline, results = make_pipeline()

    def queue(x):
        fut = FakeFuture()
        pipeline.queue(fut)

        def resolve():
            fut.set_result(x)
            return fut

        return resolve

    resolves = tuple(queue(v) for v in case)
    futures = create_futures(resolves, case)

    assert pipeline.empty

    del resolves

    # this loop is not pythonic on purpose
    # carefully don't create extra references
    for i in range(len(futures)):
        print(sys.getrefcount(futures[i]))
    del i

    assert results == case

    gc.collect()

    del futures

    gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()

    print(gc.garbage)
    gc.set_debug(0)

    assert FakeFuture.cnt == 0


def parametrize_loop():
    return pytest.mark.parametrize(
        'loop', [uvloop.new_event_loop(), asyncio.new_event_loop()],
        ids=['uv', 'aio'])


@parametrize_case([
    '1', '1@1',
    '1+2', '2+1', '2+1@1', '1@1+2',
    '1+2+3', '3+2+1', '2+1+3', '3+1+2',
    '1+3+2+1', '1+3+2+1+1@1', '1+1+3+2', '3+2+1+1', '1+1+2+3'
])
@parametrize_make_pipeline()
@parametrize_loop()
def test_real_task(loop, make_pipeline, case):
    DIVISOR = 1000
    pipeline, results = make_pipeline()

    async def coro(example):
        await asyncio.sleep(example.value / DIVISOR, loop=loop)

        return example

    def queue(x):
        task = loop.create_task(coro(x))
        pipeline.queue(task)

    for v in case:
        if v.delay:
            loop.call_later(v.delay / DIVISOR, partial(queue, v))
        else:
            queue(v)

    duration = max((e.value + e.delay) / DIVISOR for e in case)
    loop.run_until_complete(asyncio.sleep(duration, loop=loop))

    # timing issue, wait a little bit more so we collect all the results
    if len(results) < len(case):
        loop.run_until_complete(asyncio.sleep(10 / DIVISOR, loop=loop))

    assert pipeline.empty
    assert results == case

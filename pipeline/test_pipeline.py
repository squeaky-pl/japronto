import gc
import sys

import asyncio
import pipeline
import pipeline.cpipeline


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


def test():
    p = pipeline.cpipeline.Pipeline()

    def queue(x):
        fut = FakeFuture()
        p.queue(fut)

        def resolve():
            fut.set_result(x)
            return fut

        return resolve

    resolves = queue(1), queue(10), queue(5), queue(1)
    futures = resolves[3](), resolves[0](), resolves[2](), resolves[1]()

    del resolves

    # this loop is not pythonic on purpose
    # carefully don't create extra references
    for i in range(len(futures)):
        print(sys.getrefcount(futures[i]))
    del i

    assert p.results == [1, 10, 5, 1]

    gc.collect()

    del futures

    gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()

    print(gc.garbage)
    gc.set_debug(0)

    assert FakeFuture.cnt == 0

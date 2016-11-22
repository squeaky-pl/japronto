import asyncio
import pipeline


class FakeLoop:
    def call_soon(self, callback, val):
        callback(val)

    def get_debug(self):
        return False

    def create_future(self):
        return asyncio.Future(loop=self)


def test():
    loop = FakeLoop()
    p = pipeline.Pipeline()

    def queue(x):
        t = loop.create_future()
        p.queue(t)

        def resolve():
            t.set_result(x)

        return resolve

    r1 = queue(1)
    r2 = queue(10)
    r3 = queue(5)
    r4 = queue(1)

    r4()
    r1()
    r3()
    r2()

    assert p.results == [1, 10, 5, 1]

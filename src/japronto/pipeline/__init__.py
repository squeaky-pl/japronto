class Pipeline:
    def __init__(self, ready):
        self._queue = []
        self._ready = ready

    @property
    def empty(self):
        return not self._queue

    def queue(self, task):
        print("queued")

        self._queue.append(task)

        task.add_done_callback(self._task_done)

    def _task_done(self, task):
        print('Done', task.result())

        pop_idx = 0
        for task in self._queue:
            if not task.done():
                break

            self.write(task)

            pop_idx += 1

        if pop_idx:
            self._queue[:pop_idx] = []

    def write(self, task):
        self._ready(task)
        print('Written', task.result())


if __name__ == '__main__':
    import asyncio

    async def coro(sleep):
        await asyncio.sleep(sleep)

        return sleep

    from uvloop import new_event_loop

    loop = new_event_loop()
    asyncio.set_event_loop(loop)

    pipeline = Pipeline()

    def queue(x):
        t = loop.create_task(coro(x))
        pipeline.queue(t)

    loop.call_later(2, lambda: queue(2))
    loop.call_later(12, lambda: queue(2))

    queue(1)
    queue(10)
    queue(5)
    queue(1)

    loop.run_forever()

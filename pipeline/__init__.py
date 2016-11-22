from functools import partial



class Pipeline:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.tail = None
        self.results = []

    def queue(self, task):
        print("queued")

        task.depends_on = self.tail
        task.written = False
        self.tail = task

        self._task_done(None, task)

    def _resolve_dependency(self, task):
        current = task.depends_on

        while current:
            if not current.done():
                break

            current = current.depends_on

        task.depends_on = current


    def _gc(self):
        while self.tail:
            if not self.tail.written:
                break

            self.tail = self.tail.depends_on


    def _task_done(self, this_task, task):
        if this_task == task:
            print('Done', task.result())
        if this_task and (not task.depends_on or task.depends_on.written):
            self.write(task)
            self._gc()
            return

        self._resolve_dependency(task)

        if this_task:
            depends_on = task.depends_on
        else:
            depends_on = task

        depends_on.add_done_callback(partial(self._task_done, task=task))


    def write(self, task):
        self.results.append(task.result())
        task.written = True
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

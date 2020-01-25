import sys
import asyncio

PY_37 = sys.version_info > (3, 7)

if PY_37:
    all_tasks = asyncio.all_tasks
else:
    def all_tasks(loop):
        return set(filter(lambda t: not t.done(), asyncio.Task.all_tasks(loop)))

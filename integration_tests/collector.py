import psutil
import sys
import time
import matplotlib.pyplot as plt
import os
import uvloop
import asyncio as aio
from functools import partial


loop = uvloop.new_event_loop()
aio.set_event_loop(loop)


def report(pid, samples):
    plt.figure(figsize=(25,10))

    x = [s['t'] for s in samples if s['type'] == 'proc']

    lines = [s for s in samples if s['type'] == 'event']

    minuss = min(s['uss'] for s in samples if s['type'] == 'proc')
    ussplot = plt.subplot(211)
    ussplot.set_title('uss')
    ussplot.plot(
        x, [s['uss'] for s in samples if s['type'] == 'proc'], '.')
    for l in lines:
#        ussplot.text(l['t'], minuss, l['event'], horizontalalignment='right',
#            rotation=-90, rotation_mode='anchor')
        ussplot.axvline(l['t'])

    connplot = plt.subplot(212)
    connplot.set_title('conn')
    connplot.plot(
        x, [s['conn'] for s in samples if s['type'] == 'proc'], '.')

    os.makedirs('.reports', exist_ok=True)
    path = '.reports/{}.png'.format(pid)
    plt.savefig(path)

    return path


async def sample_process(pid, samples):
    process = psutil.Process(pid)

    while 1:
        try:
            uss = process.memory_full_info().uss
            conn = len(process.connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break

        samples.append({
            't': time.monotonic(),
            'uss': uss, 'conn': conn, 'type': 'proc'})
        await aio.sleep(.5)


async def receive_samples(tasks, samples, reader, writer):
    task = aio.Task.current_task()
    tasks.add(task)
    while 1:
        line = await reader.readline()
        if not line:
            break
        samples.append({
            't': time.monotonic(),
            'event': line.decode('utf-8'), 'type': 'event'})
    tasks.remove(task)


def main():
    pid = int(sys.argv[1])
    samples = []
    server_tasks = set()

    server_coro = aio.start_server(
        partial(receive_samples, server_tasks, samples), '0.0.0.0', 8081)

    server = loop.run_until_complete(server_coro)
    loop.run_until_complete(sample_process(pid, samples))
    server.close()
    for t in server_tasks:
        t.cancel()
    loop.run_until_complete(server.wait_closed())
    loop.close()

    path = report(pid, samples)
    print('Report saved to:', path)


if __name__ == '__main__':
    main()

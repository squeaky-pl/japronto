import argparse
import sys
import asyncio as aio
import os
from asyncio.subprocess import PIPE, STDOUT
import statistics
import shlex

import uvloop
import psutil

import cpu
import buggers


def run_wrk(loop, endpoint=None):
    endpoint = endpoint or 'http://localhost:8080'
    wrk_fut = aio.create_subprocess_exec(
        './wrk', '-t', '1', '-c', '100', '-d', '2', endpoint,
        stdout=PIPE, stderr=STDOUT)

    wrk = loop.run_until_complete(wrk_fut)

    lines = []
    while 1:
        line = loop.run_until_complete(wrk.stdout.readline())
        if line:
            line = line.decode('utf-8')
            lines.append(line)
            if line.startswith('Requests/sec:'):
                rps = float(line.split()[-1])
        else:
            break

    retcode = loop.run_until_complete(wrk.wait())
    if retcode != 0:
        print('\r\n'.join(lines))

    return rps


def cpu_usage(p):
    return p.cpu_percent() + sum(c.cpu_percent() for c in p.children())


def connections(process):
    return len(
        set(c.fd for c in process.connections()) |
        set(c.fd for p in process.children() for c in p.connections()))


def memory(p):
    return p.memory_percent('uss') \
        + sum(c.memory_percent('uss') for c in p.children())


if __name__ == '__main__':
    buggers.silence()
    loop = uvloop.new_event_loop()

    argparser = argparse.ArgumentParser('do_wrk')
    argparser.add_argument('-s', dest='server', default='')
    argparser.add_argument('-e', dest='endpoint')
    argparser.add_argument(
        '--no-cpu', dest='cpu_change', default=True,
        action='store_const', const=False)

    args = argparser.parse_args(sys.argv[1:])

    if args.cpu_change:
        cpu.change('userspace', cpu.min_freq())
    cpu.dump()

    aio.set_event_loop(loop)

    os.putenv('PYTHONPATH', 'src')
    server_fut = aio.create_subprocess_exec(
        'python', 'examples/hello/hello.py', *args.server.split())
    server = loop.run_until_complete(server_fut)
    os.unsetenv('PYTHONPATH')
    process = psutil.Process(server.pid)

    cpu_p = 100
    while cpu_p > 5:
        cpu_p = psutil.cpu_percent(interval=1)
        print('CPU usage in 1 sec:', cpu_p)

    results = []
    cpu_usages = []
    process_cpu_usages = []
    mem_usages = []
    conn_cnt = []
    process.cpu_percent()
    for _ in range(10):
        results.append(run_wrk(loop, args.endpoint))
        cpu_usages.append(psutil.cpu_percent())
        process_cpu_usages.append(cpu_usage(process))
        conn_cnt.append(connections(process))
        mem_usages.append(round(memory(process), 2))
        print('.', end='')
        sys.stdout.flush()

    server.terminate()
    loop.run_until_complete(server.wait())

    if args.cpu_change:
        cpu.change('ondemand')

    print()
    print('RPS', results)
    print('Mem', mem_usages)
    print('Conn', conn_cnt)
    print('Server', process_cpu_usages)
    print('System', cpu_usages)
    median = statistics.median_grouped(results)
    stdev = round(statistics.stdev(results), 2)
    p = round((stdev / median) * 100, 2)
    print('median:', median, 'stdev:', stdev, '%', p)

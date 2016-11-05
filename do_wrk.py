import argparse
import sys
import asyncio as aio
from asyncio.subprocess import PIPE, STDOUT
import statistics
import shlex

import uvloop

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


if __name__ == '__main__':
    cpu.dump()
    buggers.silence()
    loop = uvloop.new_event_loop()

    argparser = argparse.ArgumentParser('do_wrk')
    argparser.add_argument('-s', dest='server', default='')
    argparser.add_argument('-e', dest='endpoint')

    args = argparser.parse_args(sys.argv[1:])

    aio.set_event_loop(loop)

    server_fut = aio.create_subprocess_exec(
        'python', 'server.py', *args.server.split())
    server = loop.run_until_complete(server_fut)

    loop.run_until_complete(aio.sleep(1))

    results = []
    for _ in range(10):
        results.append(run_wrk(loop, args.endpoint))
        print('.', end='')
        sys.stdout.flush()

    print()
    print(results)
    print(statistics.median_grouped(results))

    server.terminate()

    loop.run_until_complete(server.wait())

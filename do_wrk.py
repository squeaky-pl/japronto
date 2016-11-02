import uvloop
import asyncio as aio
import sys
import statistics
import cpu
from asyncio.subprocess import PIPE, STDOUT


def run_wrk(loop, endpoint=None):
    endpoint = endpoint or 'http://localhost:8080'
    wrk_fut = aio.create_subprocess_exec(
        './wrk', '-t', '1', '-c', '100', '-d', '2', endpoint,
        stdout=PIPE, stderr=STDOUT)

    wrk = loop.run_until_complete(wrk_fut)

    while 1:
        line = loop.run_until_complete(wrk.stdout.readline())
        if line:
            line = line.decode('utf-8')
            if line.startswith('Requests/sec:'):
                rps = float(line.split()[-1])
        else:
            break

    loop.run_until_complete(wrk.wait())

    return rps


if __name__ == '__main__':
    cpu.dump()
    loop = uvloop.new_event_loop()

    aio.set_event_loop(loop)

    server_fut = aio.create_subprocess_exec('python', 'server.py')
    server = loop.run_until_complete(server_fut)

    endpoint = sys.argv[1] if len(sys.argv) == 2 else None
    results = []
    for _ in range(10):
        results.append(run_wrk(loop, endpoint))
        print('.', end='')
        sys.stdout.flush()

    print()
    print(results)
    print(statistics.median_grouped(results))

    server.terminate()

    loop.run_until_complete(server.wait())

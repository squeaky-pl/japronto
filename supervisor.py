import asyncio as aio
import uvloop


def supervise():
    loop = uvloop.new_event_loop()

    aio.set_event_loop(loop)

    processes = []
    for _ in range(2):
        process = loop.run_until_complete(
            aio.create_subprocess_exec('python', 'server.py'))
        processes.append(process)

    loop.run_until_complete(aio.gather(*(p.wait() for p in processes)))

    loop.close()


if __name__ == '__main__':
    supervise()

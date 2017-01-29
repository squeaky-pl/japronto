import asyncio
from japronto import Application


def synchronous(request):
    return request.Response(text='I am synchronous!')


async def asynchronous(request):
    for i in range(1, 4):
        await asyncio.sleep(1)
        print(i, 'seconds elapsed')

    return request.Response(text='3 seconds elapsed')


app = Application()

r = app.router
r.add_route('/sync', synchronous)
r.add_route('/async', asynchronous)

app.run()

import asyncio

from japronto.app import Application


def slash(request):
    return request.Response()


async def sleep(request):
    await asyncio.sleep(int(request.match_dict['sleep']))
    return request.Response()


app = Application()

r = app.router
r.add_route('/', slash)
r.add_route('/sleep/{sleep}', sleep)


if __name__ == '__main__':
    app.serve()

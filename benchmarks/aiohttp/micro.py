from aiohttp import web
import asyncio
import sys
import uvloop

loop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)

async def handle(request):
    return web.Response(text='Hello world!')

app = web.Application(loop=loop)
app.router.add_route('GET', '/', handle)

web.run_app(app, port=8080, access_log=None)

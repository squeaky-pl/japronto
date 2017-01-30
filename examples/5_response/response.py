import random
from http.cookies import SimpleCookie

from japronto.app import Application


# Providing just text argument yields a `text/plain` response
# encoded with `utf8` codec (charset set accordingly)
def text(request):
    return request.Response(text='Hello world!')


# You can override encoding by providing `encoding` attribute.
def encoding(request):
    return request.Response(text='Já pronto!', encoding='iso-8859-1')


# You can also set a custom MIME type.
def mime(request):
    return request.Response(
        mime_type="image/svg+xml",
        text="""
        <svg xmlns="http://www.w3.org/2000/svg" version="1.1">
            <line x1="10" y1="10" x2="80" y2="80" stroke="blue" />
        </svg>
        """)


# Or serve binary data. `Content-Type` set to `appilication/octet-stream`
# automtically but you can always provide your own `mime_type`.
def body(request):
    return request.Response(body=b'\xde\xad\xbe\xef')


# There exist a shortcut `json` argument. This automatically encodes the
# provided object as JSON and servers it with `Content-Type` set to
# `application/json; charset=utf8`
def json(request):
    return request.Response(json={'hello': 'world'})


# You can change the default 200 status `code` for another
def code(request):
    return request.Response(code=random.choice([200, 201, 400, 404, 500]))


# And of course you can provide custom `headers`.
def headers(request):
    return request.Response(
        text='headers',
        headers={'X-Header': 'Value',
                 'Refresh': '5; url=https://xkcd.com/353/'})


# Or `cookies` by using Python standard library `http.cookies.SimpleCookie`.
def cookies(request):
    cookies = SimpleCookie()
    cookies['hello'] = 'world'
    cookies['hello']['domain'] = 'localhost'
    cookies['hello']['path'] = '/'
    cookies['hello']['max-age'] = 3600
    cookies['city'] = 'São Paulo'

    return request.Response(text='cookies', cookies=cookies)


app = Application()
router = app.router
router.add_route('/text', text)
router.add_route('/encoding', encoding)
router.add_route('/mime', mime)
router.add_route('/body', body)
router.add_route('/json', json)
router.add_route('/code', code)
router.add_route('/headers', headers)
router.add_route('/cookies', cookies)
app.run()

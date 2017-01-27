import urllib.parse
from json import loads as json_loads
import cgi
import encodings.idna
from http.cookies import SimpleCookie, _unquote as unquote_cookie


class HttpRequest(object):
    __slots__ = ('path', 'method', 'version', 'headers', 'body')

    def __init__(self, method, path, version, headers):
        self.path = path
        self.method = method
        self.version = version
        self.headers = headers
        self.body = None

    def dump_headers(self):
        print('path', self.path)
        print('method', self.method)
        print('version', self.version)
        for n, v in self.headers.items():
            print(n, v)

    def __repr__(self):
        return '<HttpRequest {0.method} {0.path} {0.version}, {1} headers>' \
            .format(self, len(self.headers))


def memoize(func):
    def wrapper(request):
        ns = request.extra.setdefault('_japronto', {})
        try:
            return ns[func.__name__]
        except KeyError:
            pass

        result = func(request)
        ns[func.__name__] = result

        return result

    return wrapper

@memoize
def text(request):
    if request.body is None:
        return None

    return request.body.decode(request.encoding or 'utf-8')


@memoize
def json(request):
    if request.body is None:
        return None

    return json_loads(request.text)


@memoize
def query(request):
    qs = request.query_string
    if not qs:
        return {}
    return dict(urllib.parse.parse_qsl(qs))


def remote_addr(request):
    return request.transport.get_extra_info('peername')[0]


@memoize
def parsed_content_type(request):
    content_type = request.headers.get('Content-Type')
    if not content_type:
        return None, {}

    return cgi.parse_header(content_type)


def mime_type(request):
    return parsed_content_type(request)[0]


def encoding(request):
    return parsed_content_type(request)[1].get('charset')


@memoize
def parsed_form_and_files(request):
    if request.mime_type == 'application/x-www-form-urlencoded':
        return dict(urllib.parse.parse_qsl(request.text)), None
    elif request.mime_type == 'multipart/form-data':
        return None, None

    return None, None


def form(request):
    return parsed_form_and_files(request)[0]


def files(request):
    return parsed_form_and_files(request)[1]


@memoize
def hostname_and_port(request):
    host = request.headers.get('Host')
    if not host:
        return None, None

    hostname, *rest = host.split(':', 1)
    port = rest[0] if rest else None

    return encodings.idna.ToUnicode(hostname), int(port)


def port(request):
    return hostname_and_port(request)[1]


def hostname(request):
    return hostname_and_port(request)[0]


def parse_cookie(cookie):
    """Parse a ``Cookie`` HTTP header into a dict of name/value pairs.
    This function attempts to mimic browser cookie parsing behavior;
    it specifically does not follow any of the cookie-related RFCs
    (because browsers don't either).
    The algorithm used is identical to that used by Django version 1.9.10.
    """
    cookiedict = {}
    for chunk in cookie.split(str(';')):
        if str('=') in chunk:
            key, val = chunk.split(str('='), 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = str(''), chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookiedict[key] = unquote_cookie(val)
    return cookiedict


@memoize
def cookies(request):
    """A dictionary of Cookie.Morsel objects."""
    cookies = SimpleCookie()
    if 'Cookie' in request.headers:
        try:
            parsed = parse_cookie(request.headers['Cookie'])
        except Exception:
            pass
        else:
            for k, v in parsed.items():
                try:
                    cookies[k] = v
                except Exception:
                    # SimpleCookie imposes some restrictions on keys;
                    # parse_cookie does not. Discard any cookies
                    # with disallowed keys.
                    pass

    return cookies

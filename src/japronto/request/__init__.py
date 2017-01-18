import urllib.parse
from json import loads as json_loads
import encodings.idna


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

def text(request):
    if request.body is None:
        return None

    return request.body.decode(request.encoding or 'utf-8')


def json(request):
    if request.body is None:
        return None

    return json_loads(request.text)


def query(request):
    qs = request.query_string
    if not qs:
        return {}
    return dict(urllib.parse.parse_qsl(qs))


def remote_addr(request):
    return request.transport.get_extra_info('peername')[0]


def mime_type(request):
    content_type = request.headers.get('Content-Type')
    if not content_type:
        return None

    return content_type.split(';')[0].strip()


def encoding(request):
    content_type = request.headers.get('Content-Type')
    if not content_type:
        return None

    _, *rest = [v.split('=') for v in content_type.split(';')]

    rest = {k.strip(): v.strip() for k, v in rest}

    return rest.get('charset')


def form(request):
    if request.mime_type == 'application/x-www-form-urlencoded':
        return dict(urllib.parse.parse_qsl(request.text))
    else:
        return None


def memoize(func):
    def wrapper(request):
        ns = request.extra.setdefault('_hl', {})
        try:
            return ns[func.__name__]
        except KeyError:
            pass

        result = func(request)
        ns[func.__name__] = result

        return result

    return wrapper


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

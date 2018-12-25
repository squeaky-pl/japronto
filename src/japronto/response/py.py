_responses = None


def factory(status_code=200, text='', mime_type='text/plain',
            encoding='utf-8'):
    global _responses
    if _responses is None:
        _responses = [Response() for _ in range(100)]

    response = _responses.pop()

    response.status_code = status_code
    response.mime_type = mime_type
    response.text = text
    response.encoding = encoding

    return response


def dispose(response):
    _responses.append(response)


class Response:
    __slots__ = ('status_code', 'mime_type', 'text', 'encoding')

    def __init__(self, status_code=200, text='', mime_type='text/plain',
                 encoding='utf-8'):
        self.status_code = status_code
        self.mime_type = mime_type
        self.text = text
        self.encoding = encoding

    def render(self):
        body = self.text.encode(self.encoding)
        data = (
            'HTTP/1.1 ', str(self.status_code), ' OK\r\n'
            'Connection: keep-alive\r\n'
            'Content-Type: ', self.mime_type, '; encoding=', self.encoding, '\r\n'
            'Content-Length: ', str(len(body)), '\r\n\r\n',
        )
        return ''.join(data).encode(self.encoding) + body

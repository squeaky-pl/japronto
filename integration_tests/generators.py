from integration_tests import strategies as st

from hypothesis.strategies import SearchStrategy


def generate_body(body, size_k):
    if size_k and body:
        if isinstance(body, list):
            length = sum(len(b) for b in body)
        else:
            length = len(body)
        body = body * ((size_k * 1024) // length + 1)

    return body


def makeval(v, default_st, default=None):
    if isinstance(v, SearchStrategy):
        return v.example()

    if v is True:
        return default_st.example()

    if v is not None:
        return v

    return default



def generate_request(*, method=None, path=None, query_string=None,
                     headers=None, body=None, size_k=None):
    request = {}
    request['method'] = makeval(method,  st.method, 'GET')
    request['path'] = makeval(path, st.path, '/')
    request['query_string'] = makeval(query_string, st.query_string)
    request['headers'] = makeval(headers, st.headers)
    request['body'] = generate_body(makeval(body, st.body), size_k)

    return request


def send_requests(conn, number, **kwargs):
    for _ in range(number):
        request = generate_request(**kwargs)
        print(request)
        conn.request(**request)
        response = conn.getresponse()
        print(response.body)

# Request Object

Request represent an incoming HTTP request with a rich set of properties. They can be divided into
three categories: Request line and headers, message body and miscellaneous.

  ```python
  # examples/4_request/request.py
  from json import JSONDecodeError

  from japronto import Application


  # Request line and headers.
  # This represents the part of a request that comes before message body.
  # Given a HTTP 1.1 `GET` request to `/basic?a=1` this would yield
  # `method` set to `GET`, `path` set to `/basic`, `version` set to `1.1`
  # `query_string` set to `a=1` and `query` set to `{'a': '1'}`.
  # Additionaly if headers are sent they will be present in `request.headers`
  # dictionary. The keys are normalized to standard `Camel-Cased` convention.
  def basic(request):
      text = """Basic request properties:
        Method: {0.method}
        Path: {0.path}
        HTTP version: {0.version}
        Query string: {0.query_string}
        Query: {0.query}""".format(request)

      if request.headers:
          text += "\nHeaders:\n"
          for name, value in request.headers.items():
              text += "      {0}: {1}\n".format(name, value)

      return request.Response(text=text)


  # Message body
  # If there is a message body attached to a request (as in a case of `POST`)
  # method the following attriutes can be used to examine it.
  # Given a `POST` request with body set to `b'J\xc3\xa1'`, `Content-Length` header set
  # to `3` and `Content-Type` header set to `text/plain; charset=utf-8` this
  # would yield `mime_type` set to `'text/plain'`, `encoding` set to `'utf-8'`,
  # `body` set to `b'J\xc3\xa1'` and `text` set to `'Já'`.
  # `form` and `files` attributes are dictionaries respectively used for HTML forms and
  # HTML file uploads. The `json` helper property will try to decode `body` as a
  # JSON document and give you resulting Python data type.
  def body(request):
      text = """Body related properties:
        Mime type: {0.mime_type}
        Encoding: {0.encoding}
        Body: {0.body}
        Text: {0.text}
        Form parameters: {0.form}
        Files: {0.files}
      """.format(request)

      try:
          json = request.json
      except JSONDecodeError:
          pass
      else:
          text += "\nJSON:\n"
          text += str(json)

      return request.Response(text=text)


  # Miscellaneous
  # `route` will point to an instance of `Route` object representing
  # route chosen by router to handle this request. `hostname` and `port`
  # represent parsed `Host` header if any. `remote_addr` is the address of
  # a client or reverse proxy. If `keep_alive` is true the client requested to
  # keep connection open after the response is delivered. `match_dict` contains
  # route placeholder values as documented in `2_router.md`. `cookies` contains
  # a dictionary of HTTP cookies if any.
  def misc(request):
      text = """Miscellaneous:
        Matched route: {0.route}
        Hostname: {0.hostname}
        Port: {0.port}
        Remote address: {0.remote_addr},
        HTTP Keep alive: {0.keep_alive}
        Match parameters: {0.match_dict}
      """.strip().format(request)

      if request.cookies:
          text += "\nCookies:\n"
          for name, value in request.cookies.items():
              text += "      {0}: {1}\n".format(name, value)

      return request.Response(text=text)


  app = Application()
  app.router.add_route('/basic', basic)
  app.router.add_route('/body', body)
  app.router.add_route('/misc', misc)
  app.run()
  ```

The source code for all the examples can be found in [examples directory](https://github.com/squeaky_pl/japronto/tree/master/examples).


**Next:** [Response object](5_response.md)

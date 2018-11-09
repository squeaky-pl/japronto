# Japronto!

[![irc: #japronto](https://img.shields.io/badge/irc-%23japronto-brightgreen.svg)](https://webchat.freenode.net/?channels=japronto)
[![Gitter japronto/Lobby](https://badges.gitter.im/japronto/Lobby.svg)](https://gitter.im/japronto/Lobby) [![Build Status](https://travis-ci.org/squeaky-pl/japronto.svg?branch=master)](https://travis-ci.org/squeaky-pl/japronto) [![PyPI](https://img.shields.io/pypi/v/japronto.svg)](https://pypi.python.org/pypi/japronto) [![PyPI version](https://img.shields.io/pypi/pyversions/japronto.svg)](https://pypi.python.org/pypi/japronto/)

__There is no new project development happening at the moment, but it's not abandoned either. Pull requests and new maintainers are welcome__.

__If you are a novice Python programmer, you don't like plumbing yourself or you don't have basic understanding of C, this project is not probably what you are looking for__.

Japronto (from Portuguese "já pronto" /ˈʒa pɾõtu/ meaning "already done") is a __screaming-fast__, __scalable__, __asynchronous__
Python 3.5+ HTTP __toolkit__ integrated with __pipelining HTTP server__ based on [uvloop](https://github.com/MagicStack/uvloop) and [picohttpparser](https://github.com/h2o/picohttpparser). It's targeted at speed enthusiasts, people who like
plumbing and early adopters.

You can read more in the [release announcement on medium](https://medium.com/@squeaky_pl/million-requests-per-second-with-python-95c137af319)

Performance
-----------

Here's a chart to help you imagine what kind of things you can do with Japronto:

![Requests per second](benchmarks/results.png)

As user @heppu points out Go’s stdlib HTTP server can be 12% faster than the graph shows when written more carefully. Also there is the awesome fasthttp server for Go that apparently is only 18% slower than Japronto in this particular benchmark. Awesome! For details see https://github.com/squeaky-pl/japronto/pull/12 and https://github.com/squeaky-pl/japronto/pull/14.

These results of a simple "Hello world" application were obtained on AWS c4.2xlarge instance. To be fair all the contestants (including Go) were running single worker process. Servers were load tested using [wrk](https://github.com/wg/wrk) with 1 thread, 100 connections and 24 simultaneous (pipelined) requests per connection (cumulative parallelism of 2400 requests).

The source code for the benchmark can be found in [benchmarks](benchmarks) directory.

The server is written in hand tweaked C trying to take advantage of modern CPUs. It relies on picohttpparser for header &
chunked-encoding parsing while uvloop provides asynchronous I/O. It also tries to save up on
system calls by combining writes together when possible.

Early preview
-------------

This is an early preview with alpha quality implementation. APIs are provisional meaning that they will change between versions and more testing is needed. Don't use it for anything serious for now and definitely don't use it in production. Please try it though and report back feedback. If you are shopping for your next project's framework I would recommend [Sanic](https://github.com/channelcat/sanic).

At the moment the work is focused on CPython but I have PyPy on my radar, though I am not gonna look into it until PyPy reaches 3.5 compatibility somewhere later this year and most known JIT regressions are removed.

Hello world
-----------

Here is how a simple web application looks like in Japronto:

```python
from japronto import Application


def hello(request):
    return request.Response(text='Hello world!')


app = Application()
app.router.add_route('/', hello)
app.run(debug=True)
```

Tutorial
--------

1. [Getting started](tutorial/1_hello.md)
2. [Asynchronous handlers](tutorial/2_async.md)
3. [Router](tutorial/3_router.md)
4. [Request object](tutorial/4_request.md)
5. [Response object](tutorial/5_response.md)
6. [Handling exceptions](tutorial/6_exceptions.md)
7. [Extending request](tutorial/7_extend.md)

Features
--------

- HTTP 1.x implementation with support for chunked uploads
- Full support for HTTP pipelining
- Keep-alive connections with configurable reaper
- Support for synchronous and asynchronous views
- Master-multiworker model based on forking
- Support for code reloading on changes
- Simple routing

License
-------

This software is distributed under [MIT License](https://en.wikipedia.org/wiki/MIT_License). This is a very permissive license that lets you use this software for any
commercial and non-commercial work. Full text of the license is
included in [LICENSE.txt](LICENSE.txt) file.

The source distribution of this software includes a copy of picohttpparser which is distributed under MIT license as well.

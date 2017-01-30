# Getting Started

Make sure you have both [pip](https://pip.pypa.io/en/stable/installing/) and at
least version 3.5 of Python before starting. On Linux you can install
directly using pip. If you are on OSX or Windows you can still develop and use
Japronto with [Docker](https://docs.docker.com/engine/installation/#/on-macos-and-windows).
Native OSX port coming soon.

Installing
----------

On Linux install Japronto with `python3 -m pip install japronto`.
On OSX and Windows or if you simply prefer Docker pull Japronto image with `docker pull japronto/japronto`.

Creating your Hello world app
-----------------------------

Copy and paste following code into a fail named `hello.py`:

  ```python
  # examples/1_hello/hello.py
  from japronto import Application


  # Views handle logic, take request as a parameter and
  # returns Response object back to the client
  def hello(request):
      return request.Response(text='Hello world!')


  # The Application instance is a fundamental concept.
  # It is a parent to all the resources and all the settings
  # can be tweaked here.
  app = Application()

  # The Router instance lets you register your handlers and execute
  # them depending on the url path and methods
  app.router.add_route('/', hello)

  # Finally start our server and handle requests until termination is
  # requested. Enabling debug lets you see request logs and stack traces.
  app.run(debug=True)
  ```

The source code for all the examples can be found in [examples directory](https://github.com/squeaky_pl/japronto/tree/master/examples).

Run it
------

On Linux run the server with just: `python3 hello.py`.

If using Docker run `docker run -P -v hello.py:/hello.py japronto/japronto /hello.py`. This will mount local `hello.py` into container as `/hello.py` which is later passed to Docker entry point.

Now open the address `http://localhost:8000` in your web browser. You should see the message *Hello world!*.

You now have a working Japronto server!


**Next:** [Asynchronous handlers](2_async.md)

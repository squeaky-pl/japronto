# Handling exceptions

There may be cases where you may want to respond with a custom response instead of a 500 Internal Server Error when an exception(s) is raised. Or you might want to override the default 404 handler. Enter exception handlers.

  ```python
  # examples/6_exceptions/exceptions.py
  from japronto import Application, RouteNotFoundException


  # Those are our custom exceptions we want to turn into 200 response.
  class KittyError(Exception):
      def __init__(self):
          self.greet = 'meow'


  class DoggieError(Exception):
      def __init__(self):
          self.greet = 'woof'


  # The two handlers below raise exceptions which will be turned
  # into 200 responses by the handlers registered later
  def cat(request):
      raise KittyError()


  def dog(request):
      raise DoggieError()


  # This handler raises ZeroDivisionError which doesnt have an error
  # handler registered so it will result in 500 Internal Server Error
  def unhandled(request):
      1 / 0


  app = Application()

  r = app.router
  r.add_route('/cat', cat)
  r.add_route('/dog', dog)
  r.add_route('/unhandled', unhandled)


  # These two are handlers for `Kitty` and `DoggyError`s.
  def handle_cat(request, exception):
      return request.Response(text='Just a kitty, ' + exception.greet)


  def handle_dog(request, exception):
      return request.Response(text='Just a doggie, ' + exception.greet)


  # You can also override default 404 handler if you want
  def handle_not_found(request, exception):
      return request.Response(code=404, text="Are you lost, pal?")


  # register all the error handlers so they are actually effective
  app.add_error_handler(KittyError, handle_cat)
  app.add_error_handler(DoggieError, handle_dog)
  app.add_error_handler(RouteNotFoundException, handle_not_found)

  app.run()
  ```

The source code for all the examples can be found in [examples directory](https://github.com/squeaky-pl/japronto/tree/master/examples).

**Next:** [Extending request](7_extend.md)

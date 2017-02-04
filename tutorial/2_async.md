# Asynchronous handlers

With Japronto you can freely combine synchronous and asynchronous handlers and
fully take advantage of both ecosystems. Choose wisely when to use asynchronous
programming. Unless you are connecting to third party APIs, want to run input-output tasks in the background, expect large
latency or do long-running blocking queries to your database you are probably
better off programming synchronously.


  ```python
  # examples/2_async/async.py
  import asyncio
  from japronto import Application


  # This is a synchronous handler.
  def synchronous(request):
      return request.Response(text='I am synchronous!')


  # This is an asynchronous handler, it spends most of the time in the event loop.
  # It wakes up every second 1 to print and finally returns after 3 seconds.
  # This does let other handlers to be executed in the same processes while
  # from the point of view of the client it took 3 seconds to complete.
  async def asynchronous(request):
      for i in range(1, 4):
          await asyncio.sleep(1)
          print(i, 'seconds elapsed')

      return request.Response(text='3 seconds elapsed')


  app = Application()

  r = app.router
  r.add_route('/sync', synchronous)
  r.add_route('/async', asynchronous)

  app.run()
  ```

The source code for all the examples can be found in [examples directory](https://github.com/squeaky-pl/japronto/tree/master/examples).


**Next:** [Router](3_router.md)

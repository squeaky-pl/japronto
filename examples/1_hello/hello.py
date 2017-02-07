from japronto import Application


# Views handle logic, take request as a parameter and
# return the Response object back to the client
def hello(request):
    return request.Response(text='Hello world!')


# The Application instance is a fundamental concept.
# It is a parent to all the resources and all the settings
# can be tweaked there.
app = Application()

# The Router instance lets you register your handlers and execute
# them depending on the url path and methods.
app.router.add_route('/', hello)

# Finally, start our server and handle requests until termination is
# requested. Enabling debug lets you see request logs and stack traces.
app.run(debug=True)

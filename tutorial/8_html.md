# Responding with HTML

Serving HTML from japronto is as simple as adding a MIME type of `text/html` to the Response. Jinja2 templating can be leveraged as well, although in the meantime you will have to do the heavy lifting of rendering templates before sending in a response.

Copy and paste following code into a file named `html.py`:

```python
# examples/8_html/html.py
from japronto import Application
from jinja2 import Template


# A view can read HTML from a file
def index(request):
    with open('index.html') as html_file:
        return request.Response(text=html_file.read(), mime_type='text/html')


# A view could also return a raw HTML string
def example(request):
    return request.Response(text='<h1>Some HTML!</h1>', mime_type='text/html')


# A view could also return a rendered jinja2 template
def jinja(request):
    template = Template('<h1>Hello {{ name }}!</h1>')
    return request.Response(text=template.render(name='World'),
                            mime_type='text/html')


# Create the japronto application
app = Application()

# Add routes to the app
app.router.add_route('/', index)
app.router.add_route('/example', example)
app.router.add_route('/jinja2', jinja)

# Start the server
app.run(debug=True)
```

The source code for all the examples can be found in [examples directory](https://github.com/squeaky-pl/japronto/tree/master/examples).


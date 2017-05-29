# examples/8_template/template.py
from japronto import Application
from jinja2 import Template


# A view can read HTML from a file
def index(request):
    with open('index.html') as html_file:
        return request.Response(text=html_file.read(), mime_type='text/html')


# A view could also return a raw HTML string
def example(request):
    return request.Response(text='<h1>Some HTML!</h1>', mime_type='text/html')


template = Template('<h1>Hello {{ name }}!</h1>')

# A view could also return a rendered jinja2 template
def jinja(request):
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


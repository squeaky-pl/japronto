from sanic import Sanic
from sanic.response import text

app = Sanic(__name__)

@app.route("/")
async def test(request):
    return text("Hello world!")

app.run(host="0.0.0.0", port=8080)

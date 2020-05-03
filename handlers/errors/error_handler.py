import sanic
import app

app.api.error_handler.add(
    sanic.exceptions.NotFound,
    lambda r, e: sanic.response.empty(status=404)
)


import aiohttp
import ujson
import app


@app.api.listener('before_server_start')
def init(api, loop):
    api.aiohttp_session = aiohttp.ClientSession(loop=loop, json_serialize=ujson.dumps)


@app.api.listener('after_server_stop')
def finish(api, loop):
    loop.run_until_complete(api.aiohttp_session.close())
    loop.close()

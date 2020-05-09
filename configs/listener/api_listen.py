import aiohttp
import ujson
import app

from motor.motor_asyncio import AsyncIOMotorClient

from services.wallet import Wallet
from utility.loading import make_blockchain


@app.api.listener('before_server_start')
async def init(api, loop):
    api.aiohttp_session = aiohttp.ClientSession(loop=loop, json_serialize=ujson.dumps)
    api.mongodb = AsyncIOMotorClient("mongodb://localhost:27017", io_loop=loop)['lightchain']
    api.wallet = Wallet(app.port)
    blockchain = await make_blockchain(api)
    api.blockchain = blockchain
    print("server start")


@app.api.listener('after_server_stop')
def finish(api, loop):
    loop.run_until_complete(api.aiohttp_session.close())
    loop.close()

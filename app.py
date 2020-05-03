import os

from sanic import Sanic
from sanic_cors import CORS
from argparse import ArgumentParser
from services.wallet import Wallet
from services.blockchain import Blockchain

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

api = Sanic()
CORS(api)

parser = ArgumentParser()
parser.add_argument('-p', '--port', default=5000)
args = parser.parse_args()
port = args.port


wallet = Wallet(port)
blockchain = Blockchain(wallet.public_key, port)


#listener
from configs.listener import api_listen

#controllers

from controllers import node_controller


# error
from handlers.errors import error_handler
import os

from sanic import Sanic
from sanic_cors import CORS

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

api = Sanic()
CORS(api)

# listener
from configs.listener import api_listen

# controllers

from controllers import node_controller

# error
from handlers.errors import error_handler

from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-p', '--port', default=5000)
args = parser.parse_args()
port = args.port

from services.blockchain import Blockchain
from utility.reader_html import ReaderHtml
from sanic.response import html, json
import app


@app.api.route('/', methods=['GET'])
async def get_node_ui(request):
    return html(ReaderHtml.get_ui("node.html"))


@app.api.route('/network', methods=['GET'])
async def get_network_ui(request):
    return html(ReaderHtml.get_ui('network.html'))


@app.api.route('/wallet', methods=['POST'])
async def create_keys(request):
    app.wallet.create_keys()
    if app.wallet.save_keys():
        app.blockchain = Blockchain(app.wallet.public_key, app.port)
        response = {
            'public_key': app.wallet.public_key,
            'private_key': app.wallet.private_key,
            'funds': await app.blockchain.get_balance()
        }
        return json(response, status=201)
    else:
        response = {
            'message': 'Saving the keys failed.'
        }
        return json(response, status=500)


@app.api.route('/wallet', methods=['GET'])
async def load_keys(request):
    if app.wallet.load_keys():
        app.blockchain = Blockchain(app.wallet.public_key, app.port)
        response = {
            'public_key': app.wallet.public_key,
            'private_key': app.wallet.private_key,
            'funds': await app.blockchain.get_balance()
        }
        return json(response, status=201)
    else:
        response = {
            'message': 'Loading the keys failed.'
        }
        return json(response, status=500)


@app.api.route('/balance', methods=['GET'])
async def get_balance(request):
    balance = await app.blockchain.get_balance()
    if balance is not None:
        response = {
            'message': 'Fetched balance successfully.',
            'funds': balance
        }
        return json(response, status=200)
    else:
        response = {
            'message': 'Loading balance failed.',
            'wallet_set_up': app.wallet.public_key is not None
        }
        return json(response, status=500)


@app.api.route('/transaction', methods=['POST'])
async def add_transaction(request):
    if app.wallet.public_key is None:
        response = {
            'message': 'No wallet set up.'
        }
        return json(response, status=400)

    values = request.json
    if not values:
        response = {
            'message': 'No data found.'
        }
        return json(response, status=400)
    required_fields = ['recipient', 'amount']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Required data is missing.'
        }
        return json(response, status=400)
    recipient = values['recipient']
    amount = values['amount']
    signature = app.wallet.sign_transaction(app.wallet.public_key, recipient, amount)
    success = await app.blockchain.add_transaction(recipient, app.wallet.public_key, signature, amount)
    if success:
        response = {
            'message': 'Successfully added transaction.',
            'transaction': {
                'sender': app.wallet.public_key,
                'recipient': recipient,
                'amount': amount,
                'signature': signature
            },
            'funds': await app.blockchain.get_balance()
        }
        return json(response, status=201)
    else:
        response = {
            'message': 'Creating a transaction failed.'
        }
        return json(response, status=500)


@app.api.route('/broadcast-transaction', methods=['POST'])
async def broadcast_transaction(request):
    values = request.json
    if not values:
        response = {'message': 'No data found.'}
        return json(response, status=400)
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(key in values for key in required):
        response = {'message': 'Some data is missing.'}
        return json(response, status=400)
    success = await app.blockchain.add_transaction(
        values['recipient'], values['sender'], values['signature'], values['amount'], is_receiving=True)
    if success:
        response = {
            'message': 'Successfully added transaction.',
            'transaction': {
                'sender': values['sender'],
                'recipient': values['recipient'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return json(response, status=201)
    else:
        response = {
            'message': 'Creating a transaction failed.'
        }
        return json(response, status=500)


@app.api.route('/broadcast-block', methods=['POST'])
async def broadcast_block(request):
    values = request.json
    if not values:
        response = {'message': 'No data found.'}
        return json(response, status=400)
    if 'block' not in values:
        response = {'message': 'Some data is missing.'}
        return json(response, status=400)
    block = values['block']
    if block['index'] == app.blockchain.chain[-1].index + 1:
        if await app.blockchain.add_block(block):
            response = {'message': 'Block added'}
            return json(response, status=201)
        else:
            response = {'message': 'Block seems invalid.'}
            return json(response, status=409)
    elif block['index'] > app.blockchain.chain[-1].index:
        response = {'message': 'Blockchain seems to be differ from local blockchain.'}
        app.blockchain.resolve_conflicts = True
        return json(response, status=200)
    else:
        response = {'message': 'Blochain seems to be shorter, block not added'}
        return json(response, status=409)


@app.api.route('/mine', methods=['POST'])
async def mine(request):
    if app.blockchain.resolve_conflicts:
        response = {'message': 'Resolve conflicts first, block not added!'}
        return json(response, status=409)
    block = await app.blockchain.mine_block()
    if block is not None:
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
        response = {
            'message': 'Block added successfully',
            'block': dict_block,
            'funds': await app.blockchain.get_balance()
        }
        return json(response, status=201)
    else:
        response = {
            'message': 'Adding a block failed.',
            'wallet_set_up': app.wallet.public_key is not None
        }
        return json(response, status=500)


@app.api.route('/resolve-conflicts', methods=['POST'])
async def resolve_conflicts(request):
    replaced = await app.blockchain.resolve()
    if replaced:
        response = {'message': 'Chain was replaced'}
    else:
        response = {'message': 'Local chain kept!'}
    return json(response, status=200)


@app.api.route('/transactions', methods=['GET'])
async def get_open_transaction(request):
    transactions = await app.blockchain.get_open_transactions()
    dict_transactions = [tx.__dict__ for tx in transactions]
    return json(dict_transactions, status=200)


@app.api.route('/chain', methods=['GET'])
async def get_chain(request):
    chain_snapshot = app.blockchain.chain
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
    return json(dict_chain, status=200)


@app.api.route('/node', methods=['POST'])
async def add_node(request):
    values = request.json
    if not values:
        response = {
            'message': 'No date attached.'
        }
        return json(response, status=400)
    if 'node' not in values:
        response = {
            'message': 'No node data found.'
        }
        return json(response, status=400)
    node = values['node']
    app.blockchain.add_peer_node(node)
    response = {
        'message': 'Node added successfully.',
        'all_nodes': await app.blockchain.get_peer_nodes()
    }
    return json(response, status=200)


@app.api.route('/node/<node_url>', methods=['DELETE'])
async def remove_node(request, node_url):
    if node_url == '' or node_url is None:
        response = {
            'message': 'No node found.'
        }
        return json(response, status=400)
    app.blockchain.remove_peer_node(node_url)
    response = {
        'message': 'Node removed',
        'all_nodes': await app.blockchain.get_peer_nodes()
    }
    return json(response, status=200)


@app.api.route('/nodes', methods=['GET'])
async def get_nodes(request):
    nodes = await app.blockchain.get_peer_nodes()
    response = {
        'all_nodes': nodes
    }
    return json(response, status=200)

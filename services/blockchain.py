import json
import aiohttp
from app import api
from pymongo import errors
from functools import reduce
from utility.hash_util import hash_block
from services.block import Block
from services.transaction import Transaction
from services.wallet import Wallet
from utility.verification import Verification

MINING_REWARD = 10


class Blockchain:
    def __init__(self, public_key):
        genesis_block = Block(0, '', [], 100, 0)
        # Init Blockchain
        self.chain = [genesis_block]
        # unhandle transaction
        self.__open_transactions = []

        self.public_key = public_key
        self.__peer_nodes = set()
        self.resolve_conflicts = False

    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, val):
        self.__chain = val

    async def get_open_transactions(self):
        return self.__open_transactions[:]

    async def load_blockchain(self):
        blockchain = []
        try:
            async for doc in api.mongodb['blockchain'].find():
                blockchain.append(doc)
            return blockchain
        except Exception:
            print("error")

    async def load_open_transactions(self):
        opentransactions = []
        try:
            async for doc in api.mongodb['open_transactions'].find():
                opentransactions.append(doc)
            return opentransactions
        except Exception:
            print("error")

    async def delete_open_transaction(self, op):
        try:
            await api.mongodb['open_transactions'].delete_one(op)
        except Exception:
            print("Error")

    async def load_peers(self):
        peernodes = []
        try:
            async for doc in api.mongodb['peer_nodes'].find():
                peernodes.append(doc)
            return peernodes
        except Exception:
            print("error")

    async def load_data(self):
        print("load")
        try:

            blockchain = await self.load_blockchain()
            updated_blockchain = []
            for block in blockchain:
                converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in
                                block['transactions']]
                updated_block = Block(block['index'], block['previous_hash'], converted_tx, block['proof'],
                                      block['timestamp'])
                updated_blockchain.append(updated_block)
            if len(updated_blockchain) > 0:
                self.chain = updated_blockchain
            load_transactions = await self.load_open_transactions()
            if len(load_transactions) == 1:
                open_transactions = load_transactions
            else:
                open_transactions = load_transactions[:-1]
            updated_transactions = []
            for tx in open_transactions:
                updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                updated_transactions.append(updated_transaction)
            self.__open_transactions = updated_transactions
            peer_nodes = await self.load_peers()
            for p in peer_nodes:
                self.__peer_nodes.add(p["ip"])
        except Exception:
            print('Handle exception....')
        finally:
            print('Cleanup!')

    async def save_data(self):

        try:
            saveable_chain = [block.__dict__ for block in [
                Block(block_el.index, block_el.previous_hash, [tx.__dict__ for tx in block_el.transactions],
                      block_el.proof, block_el.timestamp) for block_el in self.__chain]]
            stringofchain = json.dumps(saveable_chain)
            dictofchain = json.loads(stringofchain)
            result = await api.mongodb['blockchain'].insert_many(dictofchain, ordered=False)
            print('inserted %d docs' % (len(result.inserted_ids),))
        except errors.BulkWriteError as e:
            panic = filter(lambda x: x['code'] != 11000, e.details['writeErrors'])
            if len(list(panic)) > 0:
                print(e.details['writeErrors'])

        try:
            if len(self.__open_transactions) > 0:
                print("op")
                stringofts = json.dumps([tx.__dict__ for tx in self.__open_transactions])
                saveable_tx = json.loads(stringofts)
                await api.mongodb['open_transactions'].insert_many(saveable_tx, ordered=False)
        except errors.BulkWriteError as e:
            panic = filter(lambda x: x['code'] != 11000, e.details['writeErrors'])
            if len(list(panic)) > 0:
                print(e.details['writeErrors'])

        try:
            if len(list(self.__peer_nodes)) > 0:
                print("peer")
                dlist = []
                for k, v in enumerate(list(self.__peer_nodes)):
                    dlist.append({"ip": v, "index": k})
                await api.mongodb['peer_nodes'].insert_many(dlist, ordered=False)
        except errors.BulkWriteError as e:
            panic = filter(lambda x: x['code'] != 11000, e.details['writeErrors'])
            if len(list(panic)) > 0:
                print(e.details['writeErrors'])

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    async def get_balance(self, sender=None):
        if sender is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = sender
        tx_sender = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in self.__chain]
        open_tx_sender = [tx.amount for tx in self.__open_transactions if tx.sender == participant]
        tx_sender.append(open_tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0, tx_sender,
                             0)

        tx_recipient = [[tx.amount for tx in block.transactions if tx.recipient == participant] for block in
                        self.__chain]
        amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0,
                                 tx_recipient, 0)

        return amount_received - amount_sent

    def get_last_blockchain_value(self):
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]

    async def add_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=False):
        transaction = Transaction(sender, recipient, signature, amount)
        if await Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            await self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        async with api.aiohttp_session.post(url, json={'sender': sender, 'recipient': recipient,
                                                                       'signature': signature,
                                                                       'amount': amount}) as rsp:
                            if rsp.status == 400 or rsp.status == 500:
                                print('Transaction declined, needs resolving')
                                return False
                    except aiohttp.ClientConnectionError:
                        continue
            return True
        return False

    async def mine_block(self):
        if self.public_key is None:
            return None
        last_block = self.__chain[-1]
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        reward_transaction = Transaction('MINING', self.public_key, '', MINING_REWARD)
        copied_transactions = self.__open_transactions[:]
        for tx in copied_transactions:
            if not Wallet.verify_transaction(tx):
                return None
        copied_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = []
        await self.save_data()
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [tx.__dict__ for tx in converted_block['transactions']]
            try:
                async with api.aiohttp_session.post(url, json={'block': converted_block}) as rsp:
                    if rsp.status == 400 or rsp.status == 500:
                        print('Block declined, needs resolving')
                    if rsp.status == 409:
                        self.resolve_conflicts = True
            except aiohttp.ClientConnectionError as cce:
                continue
        return block

    async def add_block(self, block):
        transactions = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in
                        block['transactions']]
        proof_is_valid = Verification.valid_proof(transactions[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(block['index'], block['previous_hash'], transactions, block['proof'],
                                block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__open_transactions[:]
        for itx in block['transactions']:
            for opentx in stored_transactions:
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] \
                        and opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transactions.remove(opentx)
                        await self.delete_open_transaction(opentx)
                    except ValueError:
                        print('Item was already removed')
        await self.save_data()
        return True

    async def resolve(self):
        winner_chain = self.chain
        replace = False
        for node in self.__peer_nodes:
            url = 'http://{}/chain'.format(node)
            try:
                async with api.aiohttp_session.get(url) as rsp:
                    node_chain = await rsp.json()
                    node_chain = [Block(block['index'], block['previous_hash'], [Transaction(
                        tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']],
                                        block['proof'], block['timestamp']) for block in node_chain]
                    node_chain_length = len(node_chain)
                    local_chain_length = len(winner_chain)
                    if node_chain_length > local_chain_length and Verification.verify_chain(node_chain):
                        winner_chain = node_chain
                        replace = True
            except aiohttp.ClientConnectionError:
                continue
        self.resolve_conflicts = False
        self.chain = winner_chain
        if replace:
            self.__open_transactions = []
        await self.save_data()
        return replace

    async def add_peer_node(self, node):
        """

        :param node: The node url which should be added
        :return:
        """
        self.__peer_nodes.add(node)
        await self.save_data()

    async def remove_peer_node(self, node):
        """
        Remove a node from peer set
        :param node:  The node url which should remove
        :return:
        """
        self.__peer_nodes.discard(node)
        await self.save_data()

    async def get_peer_nodes(self):
        """
        Return a list connect peer nodes
        :return:
        """
        return list(self.__peer_nodes)
from services.blockchain import Blockchain


async def make_blockchain(api):
    blockchain = Blockchain(api.wallet.public_key)
    await blockchain.load_data()
    return blockchain
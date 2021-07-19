from algosdk.v2client.algod import AlgodClient
from .pools import Pool

class TinymanClient:
    def __init__(self, algod_client: AlgodClient, validator_app_id: int):
        self.algod = algod_client
        self.validator_app_id = validator_app_id
    
    def get_pool(self, asset1_id, asset2_id, fetch=True):
        return Pool(self.algod, self.validator_app_id, asset1_id, asset2_id, fetch=fetch)

import json
from base64 import b64decode
from algosdk.v2client.algod import AlgodClient
from algosdk.error import AlgodHTTPError
from algosdk.encoding import encode_address
from algosdk.future.transaction import wait_for_confirmation
from tinyman.assets import Asset, AssetAmount
from .optin import prepare_app_optin_transactions,prepare_asset_optin_transactions
from .constants import TESTNET_VALIDATOR_APP_ID, MAINNET_VALIDATOR_APP_ID

class TinymanClient:
    def __init__(self, algod_client: AlgodClient, validator_app_id: int, user_address=None):
        self.algod = algod_client
        self.validator_app_id = validator_app_id
        self.assets_cache = {}
        self.user_address = user_address
    
    def fetch_pool(self, asset1, asset2, fetch=True):
        from .pools import Pool
        return Pool(self, asset1, asset2, fetch=fetch)

    def fetch_asset(self, asset_id):
        if asset_id not in self.assets_cache:
            asset = Asset(asset_id)
            asset.fetch(self.algod)
            self.assets_cache[asset_id] = asset
        return self.assets_cache[asset_id]


    def submit(self, transaction_group, wait=False):
        txid = self.algod.send_transactions(transaction_group.signed_transactions)
        if wait:
            txinfo = wait_for_confirmation(self.algod, txid)
            txinfo["txid"] = txid
            return txinfo
        return {'txid': txid}

    def prepare_app_optin_transactions(self, user_address=None):
        user_address = user_address or self.user_address
        suggested_params = self.algod.suggested_params()
        txn_group = prepare_app_optin_transactions(
            validator_app_id=self.validator_app_id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_asset_optin_transactions(self, asset_id, user_address=None):
        assert asset_id != 0, "Cannot opt into ALGO"
        user_address = user_address or self.user_address
        suggested_params = self.algod.suggested_params()
        txn_group = prepare_asset_optin_transactions(
            asset_id=asset_id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def fetch_excess_amounts(self, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        try:
            validator_app = [a for a in account_info['apps-local-state'] if a['id'] == self.validator_app_id][0]
        except IndexError:
            return {}
        try:
            validator_app_state = {x['key']: x['value'] for x in validator_app['key-value']}
        except KeyError:
            return {}

        pools = {}
        for key in validator_app_state:
            b = b64decode(key.encode())
            if b[-9:-8] == b'e':
                value = validator_app_state[key]['uint']
                pool_address = encode_address(b[:-9])
                pools[pool_address] = pools.get(pool_address, {})
                asset_id = int.from_bytes(b[-8:], 'big')
                asset = self.fetch_asset(asset_id)
                pools[pool_address][asset] = AssetAmount(asset, value)

        return pools
    
    def is_opted_in(self, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        for a in account_info.get('apps-local-state', []):
            if a['id'] == self.validator_app_id:
                return True
        return False

    def asset_is_opted_in(self, asset_id, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        for a in account_info.get('assets', []):
            if a['asset-id']==asset_id:
                return True
        return False


class TinymanTestnetClient(TinymanClient):
    def __init__(self, algod_client: AlgodClient, user_address=None):
        super().__init__(algod_client, validator_app_id=TESTNET_VALIDATOR_APP_ID, user_address=user_address)


class TinymanMainnetClient(TinymanClient):
    def __init__(self, algod_client: AlgodClient, user_address=None):
        super().__init__(algod_client, validator_app_id=MAINNET_VALIDATOR_APP_ID, user_address=user_address)

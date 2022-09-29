from base64 import b64decode
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import encode_address
from tinyman.assets import AssetAmount
from tinyman.client import BaseTinymanClient
from tinyman.staking.constants import (
    TESTNET_STAKING_APP_ID,
    MAINNET_STAKING_APP_ID,
)

from tinyman.optin import prepare_app_optin_transactions
from tinyman.v1.constants import (
    TESTNET_VALIDATOR_APP_ID,
    MAINNET_VALIDATOR_APP_ID,
)


class TinymanClient(BaseTinymanClient):
    def fetch_pool(self, asset1, asset2, fetch=True):
        from .pools import Pool

        return Pool(self, asset1, asset2, fetch=fetch)

    def prepare_app_optin_transactions(self, user_address=None):
        user_address = user_address or self.user_address
        suggested_params = self.algod.suggested_params()
        txn_group = prepare_app_optin_transactions(
            validator_app_id=self.validator_app_id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def fetch_excess_amounts(self, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        try:
            validator_app = [
                a
                for a in account_info["apps-local-state"]
                if a["id"] == self.validator_app_id
            ][0]
        except IndexError:
            return {}
        try:
            validator_app_state = {
                x["key"]: x["value"] for x in validator_app["key-value"]
            }
        except KeyError:
            return {}

        pools = {}
        for key in validator_app_state:
            b = b64decode(key.encode())
            if b[-9:-8] == b"e":
                value = validator_app_state[key]["uint"]
                pool_address = encode_address(b[:-9])
                pools[pool_address] = pools.get(pool_address, {})
                asset_id = int.from_bytes(b[-8:], "big")
                asset = self.fetch_asset(asset_id)
                pools[pool_address][asset] = AssetAmount(asset, value)

        return pools


class TinymanTestnetClient(TinymanClient):
    def __init__(self, algod_client: AlgodClient, user_address=None):
        super().__init__(
            algod_client,
            validator_app_id=TESTNET_VALIDATOR_APP_ID,
            user_address=user_address,
            staking_app_id=TESTNET_STAKING_APP_ID,
        )


class TinymanMainnetClient(TinymanClient):
    def __init__(self, algod_client: AlgodClient, user_address=None):
        super().__init__(
            algod_client,
            validator_app_id=MAINNET_VALIDATOR_APP_ID,
            user_address=user_address,
            staking_app_id=MAINNET_STAKING_APP_ID,
        )

from typing import Optional

from algosdk.v2client.algod import AlgodClient
from algosdk.future.transaction import wait_for_confirmation
from requests import request, HTTPError

from tinyman.assets import Asset
from tinyman.optin import prepare_asset_optin_transactions
from tinyman.swap_router.constants import FIXED_INPUT_SWAP_TYPE, FIXED_OUTPUT_SWAP_TYPE


class BaseTinymanClient:
    def __init__(
        self,
        algod_client: AlgodClient,
        validator_app_id: int,
        api_base_url: Optional[str] = None,
        user_address: str = None,
        staking_app_id: Optional[int] = None,
    ):
        self.algod = algod_client
        self.api_base_url = api_base_url
        self.validator_app_id = validator_app_id
        self.staking_app_id = staking_app_id
        self.assets_cache = {}
        self.user_address = user_address

    def fetch_pool(self, *args, **kwargs):
        raise NotImplementedError()

    def fetch_asset(self, asset_id):
        if asset_id not in self.assets_cache:
            asset = Asset(asset_id)
            asset.fetch(self.algod)
            self.assets_cache[asset_id] = asset
        return self.assets_cache[asset_id]

    def submit(self, transaction_group, wait=False):
        txid = self.algod.send_transactions(transaction_group.signed_transactions)
        if wait:
            txn_info = wait_for_confirmation(self.algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def prepare_asset_optin_transactions(
        self, asset_id, user_address=None, suggested_params=None
    ):
        user_address = user_address or self.user_address
        if suggested_params is None:
            suggested_params = self.algod.suggested_params()
        txn_group = prepare_asset_optin_transactions(
            asset_id=asset_id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def is_opted_in(self, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        for a in account_info.get("apps-local-state", []):
            if a["id"] == self.validator_app_id:
                return True
        return False

    def asset_is_opted_in(self, asset_id, user_address=None):
        user_address = user_address or self.user_address
        account_info = self.algod.account_info(user_address)
        for a in account_info.get("assets", []):
            if a["asset-id"] == asset_id:
                return True
        return False

    def fetch_best_swap_route(self, asset_in_id: int, asset_out_id: int, swap_type: str, amount: int):
        assert swap_type in (FIXED_INPUT_SWAP_TYPE, FIXED_OUTPUT_SWAP_TYPE)
        assert amount > 0
        assert asset_in_id >= 0
        assert asset_out_id >= 0

        data = {
            "asset_in_id": str(asset_in_id),
            "asset_out_id": str(asset_out_id),
            "swap_type": swap_type,
            "amount": str(amount)
        }

        response = request(
            method="POST",
            url=self.api_base_url + "v1/swap-router/",
            json=data,
        )
        if response.status_code != 200:
            breakpoint()
            raise HTTPError(response=response)
        response_data = response.json()

        # TODO: Handle the response and create transactions.
        print(response_data)
        raise NotImplementedError()

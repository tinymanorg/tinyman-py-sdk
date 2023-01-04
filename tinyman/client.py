from typing import Optional

from algosdk.future.transaction import wait_for_confirmation
from algosdk.v2client.algod import AlgodClient

from tinyman.assets import Asset
from tinyman.optin import prepare_asset_optin_transactions
from tinyman.utils import get_version, generate_app_call_note


class BaseTinymanClient:
    def __init__(
        self,
        algod_client: AlgodClient,
        validator_app_id: int,
        user_address=None,
        staking_app_id: Optional[int] = None,
        client_name: Optional[str] = None,
    ):
        self.algod = algod_client
        self.validator_app_id = validator_app_id
        self.staking_app_id = staking_app_id
        self.assets_cache = {}
        self.user_address = user_address
        self.client_name = client_name

    def fetch_pool(self, *args, **kwargs):
        raise NotImplementedError()

    def fetch_asset(self, asset_id):
        if asset_id not in self.assets_cache:
            asset = Asset(asset_id)
            asset.fetch(self.algod)
            self.assets_cache[asset_id] = asset
        return self.assets_cache[asset_id]

    def submit(self, transaction_group, wait=False):
        try:
            txid = self.algod.send_transactions(transaction_group.signed_transactions)
        except Exception as e:
            self.handle_error(e, transaction_group)
        if wait:
            txn_info = wait_for_confirmation(self.algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def handle_error(self, exception, transaction_group):
        error_message = str(exception)
        raise Exception(error_message) from None

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

    @property
    def version(self) -> str:
        return get_version(self.validator_app_id)

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

    def generate_app_call_note(self, client_name: Optional[str] = None):
        note = generate_app_call_note(
            version=self.version,
            client_name=client_name or self.client_name,
        )
        return note

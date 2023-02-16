from typing import Optional

from algosdk.v2client.algod import AlgodClient

from tinyman.client import BaseTinymanClient
from tinyman.errors import LogicError
from tinyman.staking.constants import (
    TESTNET_STAKING_APP_ID,
    MAINNET_STAKING_APP_ID,
)
from tinyman.swap_router.constants import (
    TESTNET_SWAP_ROUTER_APP_ID_V1,
    MAINNET_SWAP_ROUTER_APP_ID_V1,
)
from tinyman.utils import find_app_id_from_txn_id, parse_error
from tinyman.v2.constants import (
    TESTNET_VALIDATOR_APP_ID,
    MAINNET_VALIDATOR_APP_ID,
)
from tinyman.v2.utils import lookup_error


class TinymanV2Client(BaseTinymanClient):
    def __init__(self, *args, **kwargs):
        self.router_app_id = kwargs.pop("router_app_id", None)
        super().__init__(*args, **kwargs)

    def fetch_pool(self, asset_a, asset_b, fetch=True):
        from .pools import Pool

        return Pool(self, asset_a, asset_b, fetch=fetch)

    def handle_error(self, exception, txn_group):
        error = parse_error(exception)
        if isinstance(error, LogicError):
            app_id = find_app_id_from_txn_id(txn_group, error.txn_id)
            if app_id in (TESTNET_VALIDATOR_APP_ID, MAINNET_VALIDATOR_APP_ID):
                error.app_id = app_id
                error.message = lookup_error(error.pc, error.message)
        raise error from None


class TinymanV2TestnetClient(TinymanV2Client):
    def __init__(
        self,
        algod_client: AlgodClient,
        user_address: Optional[str] = None,
        client_name: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        super().__init__(
            algod_client,
            validator_app_id=TESTNET_VALIDATOR_APP_ID,
            router_app_id=TESTNET_SWAP_ROUTER_APP_ID_V1,
            api_base_url=api_base_url or "https://testnet.analytics.tinyman.org/api/",
            user_address=user_address,
            staking_app_id=TESTNET_STAKING_APP_ID,
            client_name=client_name,
        )


class TinymanV2MainnetClient(TinymanV2Client):
    def __init__(
        self,
        algod_client: AlgodClient,
        user_address: Optional[str] = None,
        client_name: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        super().__init__(
            algod_client,
            validator_app_id=MAINNET_VALIDATOR_APP_ID,
            router_app_id=MAINNET_SWAP_ROUTER_APP_ID_V1,
            api_base_url=api_base_url or "https://mainnet.analytics.tinyman.org/api/",
            user_address=user_address,
            staking_app_id=MAINNET_STAKING_APP_ID,
            client_name=client_name,
        )

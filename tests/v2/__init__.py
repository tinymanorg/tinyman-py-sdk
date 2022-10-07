from unittest import TestCase

from algosdk.v2client.algod import AlgodClient

from tinyman.v2.client import TinymanV2Client
from tests import get_suggested_params


class BaseTestCase(TestCase):
    maxDiff = None

    @classmethod
    def get_tinyman_client(cls, user_address=None):
        return TinymanV2Client(
            algod_client=AlgodClient("TEST", "https://test.test.network"),
            validator_app_id=cls.VALIDATOR_APP_ID,
            user_address=user_address or cls.user_address,
            staking_app_id=None,
        )

    @classmethod
    def get_suggested_params(cls):
        return get_suggested_params()

    @classmethod
    def get_pool_state(
        cls, asset_1_id=None, asset_2_id=None, pool_token_asset_id=None, **kwargs
    ):
        state = {
            "asset_1_cumulative_price": 0,
            "lock": 0,
            "cumulative_price_update_timestamp": 0,
            "asset_2_cumulative_price": 0,
            "asset_2_protocol_fees": 0,
            "asset_1_reserves": 0,
            "pool_token_asset_id": pool_token_asset_id or cls.pool_token_asset_id,
            "asset_1_protocol_fees": 0,
            "asset_1_id": asset_1_id or cls.asset_1_id,
            "asset_2_id": asset_2_id or cls.asset_2_id,
            "issued_pool_tokens": 0,
            "asset_2_reserves": 0,
            "protocol_fee_ratio": 6,
            "total_fee_share": 30,
        }
        state.update(**kwargs)
        return state

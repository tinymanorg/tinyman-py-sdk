from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import APPCALL_TXN
from algosdk.encoding import decode_address
from tinyman.compat import OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.utils import int_to_bytes
from tinyman.v2.constants import (
    FLASH_SWAP_APP_ARGUMENT,
    VERIFY_FLASH_SWAP_APP_ARGUMENT,
    TESTNET_VALIDATOR_APP_ID_V2,
)
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.flash_swap import prepare_flash_swap_transactions
from tinyman.v2.pools import Pool


class FlashSwapTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID = TESTNET_VALIDATOR_APP_ID_V2
        cls.sender_private_key, cls.user_address = generate_account()
        cls.asset_1_id = 10
        cls.asset_2_id = 8
        cls.pool_token_asset_id = 15
        cls.pool_address = get_pool_logicsig(
            cls.VALIDATOR_APP_ID, cls.asset_1_id, cls.asset_2_id
        ).address()
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)
        cls.pool_state = cls.get_pool_state(
            asset_1_reserves=10_000_000,
            asset_2_reserves=1_000_000_000,
            issued_pool_tokens=100_000_000,
        )
        cls.pool = Pool.from_state(
            address=cls.pool_address,
            state=cls.pool_state,
            round_number=100,
            client=cls.get_tinyman_client(),
        )

    def test_flash_swap(self):
        index_diff = 1
        txn_group = prepare_flash_swap_transactions(
            validator_app_id=self.VALIDATOR_APP_ID,
            asset_1_id=self.pool.asset_1.id,
            asset_2_id=self.pool.asset_2.id,
            asset_1_loan_amount=1_000_000,
            asset_2_loan_amount=100_000_000,
            transactions=[],
            sender=self.user_address,
            suggested_params=self.get_suggested_params(),
            app_call_note=self.app_call_note().decode(),
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "apaa": [
                    FLASH_SWAP_APP_ARGUMENT,
                    int_to_bytes(index_diff),
                    int_to_bytes(1_000_000),
                    int_to_bytes(100_000_000),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apat": [decode_address(self.pool.address)],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 3000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": APPCALL_TXN,
                "note": self.app_call_note(),
            },
        )

        # Verify
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    VERIFY_FLASH_SWAP_APP_ARGUMENT,
                    int_to_bytes(index_diff),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apat": [decode_address(self.pool.address)],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": APPCALL_TXN,
                "note": self.app_call_note(),
            },
        )

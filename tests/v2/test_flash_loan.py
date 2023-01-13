from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import APPCALL_TXN
from algosdk.encoding import decode_address
from algosdk.future.transaction import AssetTransferTxn, OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.assets import AssetAmount
from tinyman.utils import int_to_bytes
from tinyman.v2.constants import (
    FLASH_LOAN_APP_ARGUMENT,
    VERIFY_FLASH_LOAN_APP_ARGUMENT,
    TESTNET_VALIDATOR_APP_ID_V2,
)
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool
from tinyman.v2.quotes import FlashLoanQuote


class FlashLoanTestCase(BaseTestCase):
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

    def test_flash_loan(self):
        quote = self.pool.fetch_flash_loan_quote(
            loan_amount_a=AssetAmount(self.pool.asset_1, 1_000_000),
            loan_amount_b=AssetAmount(self.pool.asset_2, 10_000_000),
            refresh=False,
        )

        self.assertEqual(type(quote), FlashLoanQuote)
        self.assertEqual(
            quote.amounts_out[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 1_000_000),
        )
        self.assertEqual(
            quote.amounts_out[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 10_000_000),
        )
        self.assertEqual(
            quote.amounts_in[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 1_003_000),
        )
        self.assertEqual(
            quote.amounts_in[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 10_030_000),
        )
        self.assertEqual(
            quote.fees[self.pool.asset_1], AssetAmount(self.pool.asset_1, 3_000)
        )
        self.assertEqual(
            quote.fees[self.pool.asset_2], AssetAmount(self.pool.asset_2, 30_000)
        )

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_flash_loan_transactions_from_quote(
            quote=quote, suggested_params=suggested_params, transactions=[]
        )
        index_diff = 3
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 4)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "apaa": [
                    FLASH_LOAN_APP_ARGUMENT,
                    int_to_bytes(index_diff),
                    int_to_bytes(quote.amounts_out[self.pool.asset_1].amount),
                    int_to_bytes(quote.amounts_out[self.pool.asset_2].amount),
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

        self.assertEqual(type(transactions[1]), AssetTransferTxn)
        self.assertEqual(transactions[1].index, self.pool.asset_1.id)
        self.assertEqual(transactions[1].sender, self.user_address)
        self.assertEqual(transactions[1].receiver, self.pool_address)
        self.assertEqual(
            transactions[1].amount, quote.amounts_in[self.pool.asset_1].amount
        )

        self.assertEqual(type(transactions[2]), AssetTransferTxn)
        self.assertEqual(transactions[2].index, self.pool.asset_2.id)
        self.assertEqual(transactions[2].sender, self.user_address)
        self.assertEqual(transactions[2].receiver, self.pool_address)
        self.assertEqual(
            transactions[2].amount, quote.amounts_in[self.pool.asset_2].amount
        )

        self.assertDictEqual(
            dict(transactions[3].dictify()),
            {
                "apaa": [
                    VERIFY_FLASH_LOAN_APP_ARGUMENT,
                    int_to_bytes(index_diff),
                ],
                "apan": OnComplete.NoOpOC,
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

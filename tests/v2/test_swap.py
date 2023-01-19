from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import ASSETTRANSFER_TXN, APPCALL_TXN
from algosdk.encoding import decode_address
from tinyman.compat import OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.assets import AssetAmount
from tinyman.utils import int_to_bytes
from tinyman.v2.constants import (
    SWAP_APP_ARGUMENT,
    FIXED_INPUT_APP_ARGUMENT,
    FIXED_OUTPUT_APP_ARGUMENT,
    TESTNET_VALIDATOR_APP_ID_V2,
)
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool
from tinyman.v2.quotes import SwapQuote


class SwapTestCase(BaseTestCase):
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

    def test_fixed_input_swap(self):
        quote = self.pool.fetch_fixed_input_swap_quote(
            amount_in=AssetAmount(self.pool.asset_1, 10_000_000), refresh=False
        )

        self.assertEqual(type(quote), SwapQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(quote.swap_type, "fixed-input")
        self.assertEqual(quote.amount_in, AssetAmount(self.pool.asset_1, 10_000_000))
        self.assertEqual(quote.amount_out, AssetAmount(self.pool.asset_2, 499_248_873))
        self.assertEqual(
            quote.amount_in_with_slippage, AssetAmount(self.pool.asset_1, 10_000_000)
        )
        self.assertEqual(
            quote.amount_out_with_slippage, AssetAmount(self.pool.asset_2, 474_286_430)
        )
        self.assertEqual(quote.swap_fees, AssetAmount(self.pool.asset_1, 300_00))
        self.assertEqual(quote.price_impact, 0.50075)

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_swap_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.amount_in.amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": quote.amount_in.asset.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    SWAP_APP_ARGUMENT,
                    FIXED_INPUT_APP_ARGUMENT,
                    int_to_bytes(quote.amount_out_with_slippage.amount),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apat": [decode_address(self.pool_address)],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 2000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": APPCALL_TXN,
                "note": self.app_call_note(),
            },
        )

    def test_fixed_output_swap(self):
        quote = self.pool.fetch_fixed_output_swap_quote(
            amount_out=AssetAmount(self.pool.asset_2, 499_248_873), refresh=False
        )

        self.assertEqual(type(quote), SwapQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(quote.swap_type, "fixed-output")
        self.assertEqual(quote.amount_in, AssetAmount(self.pool.asset_1, 10_000_000))
        self.assertEqual(quote.amount_out, AssetAmount(self.pool.asset_2, 499_248_873))
        self.assertEqual(
            quote.amount_in_with_slippage, AssetAmount(self.pool.asset_1, 10_500_000)
        )
        self.assertEqual(
            quote.amount_out_with_slippage, AssetAmount(self.pool.asset_2, 499_248_873)
        )
        self.assertEqual(quote.swap_fees, AssetAmount(self.pool.asset_1, 300_00))
        self.assertEqual(quote.price_impact, 0.50075)

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_swap_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.amount_in_with_slippage.amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": quote.amount_in.asset.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    SWAP_APP_ARGUMENT,
                    FIXED_OUTPUT_APP_ARGUMENT,
                    int_to_bytes(quote.amount_out.amount),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apat": [decode_address(self.pool_address)],
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

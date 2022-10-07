from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import ASSETTRANSFER_TXN, APPCALL_TXN
from algosdk.encoding import decode_address
from algosdk.future.transaction import OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.assets import AssetAmount
from tinyman.utils import int_to_bytes
from tinyman.v2.constants import REMOVE_LIQUIDITY_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool
from tinyman.v2.quotes import RemoveLiquidityQuote, SingleAssetRemoveLiquidityQuote


class RemoveLiquidityTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID = 12345
        cls.sender_private_key, cls.user_address = generate_account()
        cls.asset_1_id = 10
        cls.asset_2_id = 8
        cls.pool_token_asset_id = 15
        cls.pool_address = get_pool_logicsig(
            cls.VALIDATOR_APP_ID, cls.asset_1_id, cls.asset_2_id
        ).address()
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)
        cls.pool_state = cls.get_pool_state(
            asset_1_reserves=1_000_000,
            asset_2_reserves=100_000_000,
            issued_pool_tokens=10_000_000,
        )
        cls.pool = Pool.from_state(
            address=cls.pool_address,
            state=cls.pool_state,
            round_number=100,
            client=cls.get_tinyman_client(),
        )

    def test_remove_liquidity(self):
        quote = self.pool.fetch_remove_liquidity_quote(
            pool_token_asset_in=5_000_000, refresh=False
        )

        self.assertEqual(type(quote), RemoveLiquidityQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(
            quote.pool_token_asset_amount,
            AssetAmount(self.pool.pool_token_asset, 5_000_000),
        )
        self.assertEqual(
            quote.amounts_out[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 500_000),
        )
        self.assertEqual(
            quote.amounts_out[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 50_000_000),
        )
        self.assertEqual(
            quote.amounts_out_with_slippage[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 475_000),
        )
        self.assertEqual(
            quote.amounts_out_with_slippage[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 47_500_000),
        )

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_remove_liquidity_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.pool_token_asset_amount.amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.pool_token_asset.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    REMOVE_LIQUIDITY_APP_ARGUMENT,
                    int_to_bytes(
                        quote.amounts_out_with_slippage[self.pool.asset_1].amount
                    ),
                    int_to_bytes(
                        quote.amounts_out_with_slippage[self.pool.asset_2].amount
                    ),
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
            },
        )

    def test_single_asset_remove_liquidity(self):
        quote = self.pool.fetch_single_asset_remove_liquidity_quote(
            pool_token_asset_in=5_000_000, output_asset=self.pool.asset_1, refresh=False
        )

        self.assertEqual(type(quote), SingleAssetRemoveLiquidityQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(
            quote.pool_token_asset_amount,
            AssetAmount(self.pool.pool_token_asset, 5_000_000),
        )
        self.assertEqual(quote.amount_out, AssetAmount(self.pool.asset_1, 749_624))
        self.assertEqual(
            quote.amount_out_with_slippage, AssetAmount(self.pool.asset_1, 712_143)
        )

        internal_swap_quote = quote.internal_swap_quote
        self.assertEqual(
            internal_swap_quote.amount_in, AssetAmount(self.pool.asset_2, 50_000_000)
        )
        self.assertEqual(
            internal_swap_quote.amount_out, AssetAmount(self.pool.asset_1, 249_624)
        )
        self.assertEqual(
            internal_swap_quote.swap_fees, AssetAmount(self.pool.asset_2, 150_000)
        )
        self.assertEqual(internal_swap_quote.price_impact, 0.50075)

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_remove_liquidity_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.pool_token_asset_amount.amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.pool_token_asset.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    REMOVE_LIQUIDITY_APP_ARGUMENT,
                    int_to_bytes(quote.amount_out_with_slippage.amount),
                    int_to_bytes(0),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.asset_1.id],
                "apat": [decode_address(self.pool_address)],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 3000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": APPCALL_TXN,
            },
        )

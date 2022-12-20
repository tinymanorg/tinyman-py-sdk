from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import ASSETTRANSFER_TXN, APPCALL_TXN
from algosdk.encoding import decode_address
from algosdk.future.transaction import OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.assets import AssetAmount
from tinyman.utils import int_to_bytes
from tinyman.v2.constants import (
    LOCKED_POOL_TOKENS,
    ADD_INITIAL_LIQUIDITY_APP_ARGUMENT,
    ADD_LIQUIDITY_APP_ARGUMENT,
    ADD_LIQUIDITY_FLEXIBLE_MODE_APP_ARGUMENT,
    ADD_LIQUIDITY_SINGLE_MODE_APP_ARGUMENT,
)
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool
from tinyman.v2.quotes import (
    InitialAddLiquidityQuote,
    FlexibleAddLiquidityQuote,
    SingleAssetAddLiquidityQuote,
)


class InitialAddLiquidityTestCase(BaseTestCase):
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
        cls.pool_state = cls.get_pool_state()

        cls.pool = Pool.from_state(
            address=cls.pool_address,
            state=cls.pool_state,
            round_number=100,
            client=cls.get_tinyman_client(),
        )

    def test_add_liquidity(self):
        asset_a_amount = AssetAmount(self.pool.asset_1, 1_000_000)
        asset_b_amount = AssetAmount(self.pool.asset_2, 100_000_000)
        quote = self.pool.fetch_initial_add_liquidity_quote(
            amount_a=asset_a_amount, amount_b=asset_b_amount, refresh=False
        )

        self.assertEqual(type(quote), InitialAddLiquidityQuote)
        self.assertEqual(
            quote.amounts_in[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 1_000_000),
        )
        self.assertEqual(
            quote.amounts_in[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 100_000_000),
        )
        self.assertEqual(
            quote.pool_token_asset_amount,
            AssetAmount(self.pool.pool_token_asset, 10_000_000 - LOCKED_POOL_TOKENS),
        )

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_add_liquidity_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 3)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.amounts_in[self.pool.asset_1].amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.asset_1.id,
            },
        )

        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "aamt": quote.amounts_in[self.pool.asset_2].amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.asset_2.id,
            },
        )

        self.assertDictEqual(
            dict(transactions[2].dictify()),
            {
                "apaa": [ADD_INITIAL_LIQUIDITY_APP_ARGUMENT],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.pool_token_asset.id],
                "apat": [decode_address(self.pool_address)],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 2000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": APPCALL_TXN,
            },
        )


class AddLiquidityTestCase(BaseTestCase):
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

    def test_flexible_add_liquidity(self):
        asset_a_amount = AssetAmount(self.pool.asset_1, 10_000_000)
        asset_b_amount = AssetAmount(self.pool.asset_2, 10_000_000)
        quote = self.pool.fetch_flexible_add_liquidity_quote(
            amount_a=asset_a_amount, amount_b=asset_b_amount, refresh=False
        )

        self.assertEqual(type(quote), FlexibleAddLiquidityQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(
            quote.amounts_in[self.pool.asset_1],
            AssetAmount(self.pool.asset_1, 10_000_000),
        )
        self.assertEqual(
            quote.amounts_in[self.pool.asset_2],
            AssetAmount(self.pool.asset_2, 10_000_000),
        )
        self.assertEqual(
            quote.pool_token_asset_amount,
            AssetAmount(self.pool.pool_token_asset, 24_774_768),
        )
        self.assertEqual(quote.min_pool_token_asset_amount_with_slippage, 23_536_029)

        internal_swap_quote = quote.internal_swap_quote
        self.assertEqual(
            internal_swap_quote.amount_in, AssetAmount(self.pool.asset_1, 2_168_784)
        )
        self.assertEqual(
            internal_swap_quote.amount_out, AssetAmount(self.pool.asset_2, 68_377_223)
        )
        self.assertEqual(
            internal_swap_quote.swap_fees, AssetAmount(self.pool.asset_1, 6_506)
        )
        self.assertEqual(internal_swap_quote.price_impact, 0.68472)

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_add_liquidity_transactions_from_quote(
            quote=quote, suggested_params=suggested_params
        )
        transactions = txn_group.transactions

        self.assertEqual(len(transactions), 3)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "aamt": quote.amounts_in[self.pool.asset_1].amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.asset_1.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "aamt": quote.amounts_in[self.pool.asset_2].amount,
                "arcv": decode_address(self.pool_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(self.user_address),
                "type": ASSETTRANSFER_TXN,
                "xaid": self.pool.asset_2.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[2].dictify()),
            {
                "apaa": [
                    ADD_LIQUIDITY_APP_ARGUMENT,
                    ADD_LIQUIDITY_FLEXIBLE_MODE_APP_ARGUMENT,
                    int_to_bytes(23_536_029),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.pool_token_asset.id],
                "apat": [decode_address(self.pool.address)],
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

    def test_single_asset_add_liquidity(self):
        asset_a_amount = AssetAmount(self.pool.asset_1, 10_000_000)
        quote = self.pool.fetch_single_asset_add_liquidity_quote(
            amount_a=asset_a_amount, refresh=False
        )

        self.assertEqual(type(quote), SingleAssetAddLiquidityQuote)
        self.assertEqual(quote.slippage, 0.05)
        self.assertEqual(quote.amount_in, AssetAmount(self.pool.asset_1, 10_000_000))
        self.assertEqual(
            quote.pool_token_asset_amount,
            AssetAmount(self.pool.pool_token_asset, 23_155_740),
        )
        self.assertEqual(quote.min_pool_token_asset_amount_with_slippage, 21_997_953)

        internal_swap_quote = quote.internal_swap_quote
        self.assertEqual(
            internal_swap_quote.amount_in, AssetAmount(self.pool.asset_1, 2_323_595)
        )
        self.assertEqual(
            internal_swap_quote.amount_out, AssetAmount(self.pool.asset_2, 69_848_864)
        )
        self.assertEqual(
            internal_swap_quote.swap_fees, AssetAmount(self.pool.asset_1, 6_970)
        )
        self.assertEqual(internal_swap_quote.price_impact, 0.69939)

        suggested_params = self.get_suggested_params()
        txn_group = self.pool.prepare_add_liquidity_transactions_from_quote(
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
                "xaid": self.pool.asset_1.id,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [
                    ADD_LIQUIDITY_APP_ARGUMENT,
                    ADD_LIQUIDITY_SINGLE_MODE_APP_ARGUMENT,
                    int_to_bytes(21_997_953),
                ],
                "apan": OnComplete.NoOpOC,
                "apas": [self.pool.pool_token_asset.id],
                "apat": [decode_address(self.pool.address)],
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

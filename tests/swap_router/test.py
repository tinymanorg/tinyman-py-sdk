from typing import Optional
from unittest import TestCase
from unittest.mock import ANY, patch

from algosdk.account import generate_account
from algosdk.encoding import decode_address
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient

from tests import get_suggested_params
from tinyman.assets import Asset, AssetAmount
from tinyman.compat import OnComplete
from tinyman.swap_router.routes import (
    Route,
    get_best_fixed_input_route,
    get_best_fixed_output_route,
)
from tinyman.swap_router.swap_router import (
    prepare_swap_router_asset_opt_in_transaction,
    prepare_swap_router_transactions,
    get_swap_router_app_opt_in_required_asset_ids,
)
from tinyman.swap_router.utils import parse_swap_router_event_log
from tinyman.v1.client import TinymanClient
from tinyman.v1.constants import TESTNET_VALIDATOR_APP_ID
from tinyman.v2.client import TinymanV2Client
from tinyman.v2.constants import TESTNET_VALIDATOR_APP_ID_V2
from tinyman.v2.contracts import get_pool_logicsig as v2_get_pool_logicsig
from tinyman.v2.pools import Pool as V2Pool
from tinyman.v2.quotes import SwapQuote as V2SwapQuote


class BaseTestCase(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID_V1 = TESTNET_VALIDATOR_APP_ID
        cls.VALIDATOR_APP_ID_V2 = TESTNET_VALIDATOR_APP_ID_V2
        cls.ROUTER_APP_ID = 987_654

    @classmethod
    def get_tinyman_client(cls, user_address=None):
        return TinymanV2Client(
            algod_client=AlgodClient("TEST", "https://test.test.network"),
            validator_app_id=cls.VALIDATOR_APP_ID_V2,
            user_address=user_address,
            router_app_id=cls.ROUTER_APP_ID,
            staking_app_id=None,
        )

    @classmethod
    def get_tinyman_v1_client(cls, user_address=None):
        return TinymanClient(
            algod_client=AlgodClient("TEST", "https://test.test.network"),
            validator_app_id=cls.VALIDATOR_APP_ID_V1,
            user_address=user_address,
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
            "pool_token_asset_id": pool_token_asset_id,
            "asset_1_protocol_fees": 0,
            "asset_1_id": asset_1_id,
            "asset_2_id": asset_2_id,
            "issued_pool_tokens": 0,
            "asset_2_reserves": 0,
            "protocol_fee_ratio": 6,
            "total_fee_share": 30,
        }
        state.update(**kwargs)
        return state

    def setUp(self) -> None:
        self.algo = Asset(id=0, name="Algorand", unit_name="Algo", decimals=6)
        # Direct Route: Pool
        self.asset_in = Asset(id=1, name="Asset In", unit_name="Asset In", decimals=6)
        self.asset_out = Asset(
            id=2, name="Asset Out", unit_name="Asset Out", decimals=10
        )
        pool_token_asset = Asset(id=3, name="TM", unit_name="TM", decimals=6)

        pool_state = self.get_pool_state(
            asset_1_id=self.asset_in.id,
            asset_2_id=self.asset_out.id,
            pool_token_asset_id=pool_token_asset.id,
            issued_pool_tokens=10_000,
        )
        pool_logicsig = v2_get_pool_logicsig(
            TESTNET_VALIDATOR_APP_ID_V2, self.asset_in.id, self.asset_out.id
        )
        self.pool = V2Pool.from_state(
            address=pool_logicsig.address(),
            state=pool_state,
            round_number=100,
            client=self.get_tinyman_client(),
        )

        # Indirect Route: Pool 1 - Pool 2
        self.intermediary_asset = Asset(id=4, name="Int", unit_name="Int", decimals=10)
        pool_1_token_asset = Asset(id=5, name="TM", unit_name="TM", decimals=6)
        pool_1_state = self.get_pool_state(
            asset_1_id=self.asset_in.id,
            asset_2_id=self.intermediary_asset.id,
            pool_token_asset_id=pool_1_token_asset.id,
            issued_pool_tokens=10_000,
        )
        pool_1_logicsig = v2_get_pool_logicsig(
            TESTNET_VALIDATOR_APP_ID_V2, self.asset_in.id, self.intermediary_asset.id
        )
        self.pool_1 = V2Pool.from_state(
            address=pool_1_logicsig.address(),
            state=pool_1_state,
            round_number=100,
            client=self.get_tinyman_client(),
        )

        pool_2_token_asset = Asset(id=6, name="TM", unit_name="TM", decimals=6)
        pool_2_state = self.get_pool_state(
            asset_1_id=self.intermediary_asset.id,
            asset_2_id=self.asset_out.id,
            pool_token_asset_id=pool_2_token_asset.id,
            issued_pool_tokens=10_000,
        )
        pool_2_logicsig = v2_get_pool_logicsig(
            TESTNET_VALIDATOR_APP_ID_V2, self.intermediary_asset.id, self.asset_out.id
        )
        self.pool_2 = V2Pool.from_state(
            address=pool_2_logicsig.address(),
            state=pool_2_state,
            round_number=100,
            client=self.get_tinyman_client(),
        )

        # Swap 1 -> 2: Price ~= 1/5
        # ID 2
        self.pool.asset_1_reserves = 1_000_000_000_000
        # ID 1
        self.pool.asset_2_reserves = 5_000_000_000_000

        # Swap 1 -> 2: Price ~= 1/2 * 1/2 = 1/4
        # ID 4
        self.pool_1.asset_1_reserves = 1_000_000_000_000
        # ID 1
        self.pool_1.asset_2_reserves = 2_000_000_000_000

        # ID 4
        self.pool_2.asset_1_reserves = 2_000_000_000_000
        # ID 2
        self.pool_2.asset_2_reserves = 1_000_000_000_000

        self.direct_route = Route(
            asset_in=self.asset_in, asset_out=self.asset_out, pools=[self.pool]
        )
        self.indirect_route = Route(
            asset_in=self.asset_in,
            asset_out=self.asset_out,
            pools=[self.pool_1, self.pool_2],
        )

    def get_mock_account_info(
        self,
        address: str,
        assets: Optional[list] = None,
        algo_balance: Optional[int] = None,
        min_balance: Optional[int] = None,
    ):
        if assets is None:
            assets = []

        total_assets_opted_in = len(assets)

        if min_balance is None:
            min_balance = 1_000
            min_balance += 100_000 * total_assets_opted_in

        if algo_balance is None:
            algo_balance = min_balance

        return {
            "address": address,
            "amount": algo_balance,
            "min-balance": algo_balance,
            "total-assets-opted-in": total_assets_opted_in,
            # [{'amount': 45682551121, 'asset-id': 10458941, 'is-frozen': False}]
            "assets": assets,
        }


class RouteTestCase(BaseTestCase):
    def test_fixed_input_quotes(self):
        amount_in = 10_000

        quotes = self.direct_route.get_fixed_input_quotes(
            amount_in=amount_in, slippage=0.05
        )
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].amount_in.amount, amount_in)
        self.assertEqual(quotes[0].amount_out.amount, 1993)

        quotes = self.indirect_route.get_fixed_input_quotes(
            amount_in=amount_in, slippage=0.05
        )
        self.assertEqual(len(quotes), 2)
        self.assertEqual(quotes[0].amount_in.amount, amount_in)
        self.assertEqual(quotes[0].amount_out.amount, 4984)
        self.assertEqual(quotes[1].amount_in.amount, 4984)
        self.assertEqual(quotes[1].amount_out.amount, 2484)

    def test_fixed_output_quotes(self):
        amount_out = 10_000

        quotes = self.direct_route.get_fixed_output_quotes(
            amount_out=amount_out, slippage=0.05
        )
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].amount_in.amount, 50151)
        self.assertEqual(quotes[0].amount_out.amount, amount_out)

        quotes = self.indirect_route.get_fixed_output_quotes(
            amount_out=amount_out, slippage=0.05
        )
        self.assertEqual(len(quotes), 2)
        self.assertEqual(quotes[0].amount_in.amount, 40243)
        self.assertEqual(quotes[0].amount_out.amount, 20061)
        self.assertEqual(quotes[1].amount_in.amount, 20061)
        self.assertEqual(quotes[1].amount_out.amount, amount_out)

    def test_fixed_input_direct_best_route(self):
        # Swap 1 -> 2: Price ~= 1/3
        # ID 2
        self.pool.asset_1_reserves = 1_000_000_000_000
        # ID 1
        self.pool.asset_2_reserves = 3_000_000_000_000

        self.direct_route = Route(
            asset_in=self.asset_in, asset_out=self.asset_out, pools=[self.pool]
        )
        routes = [self.direct_route, self.indirect_route]

        amount_in = 10_000
        best_route = get_best_fixed_input_route(routes=routes, amount_in=amount_in)
        self.assertEqual(best_route, self.direct_route)

        quotes = best_route.get_fixed_input_quotes(amount_in=amount_in)
        last_quote = quotes[-1]
        self.assertEqual(last_quote.amount_out.amount, 3323)

    def test_fixed_input_indirect_best_route(self):
        routes = [self.direct_route, self.indirect_route]

        amount_in = 10_000
        best_route = get_best_fixed_input_route(routes=routes, amount_in=amount_in)
        self.assertEqual(best_route, self.indirect_route)

        quotes = best_route.get_fixed_input_quotes(amount_in=amount_in)
        last_quote = quotes[-1]
        self.assertEqual(last_quote.amount_out.amount, 2484)

    def test_fixed_output_direct_best_route(self):
        # Swap 1 -> 2: Price ~= 1/3
        # ID 2
        self.pool.asset_1_reserves = 1_000_000_000_000
        # ID 1
        self.pool.asset_2_reserves = 3_000_000_000_000

        self.direct_route = Route(
            asset_in=self.asset_in, asset_out=self.asset_out, pools=[self.pool]
        )
        routes = [self.direct_route, self.indirect_route]

        amount_out = 10_000
        best_route = get_best_fixed_output_route(routes=routes, amount_out=amount_out)
        self.assertEqual(best_route, self.direct_route)

        quotes = best_route.get_fixed_output_quotes(amount_out=amount_out)
        first_quote = quotes[0]
        self.assertEqual(first_quote.amount_in.amount, 30091)
        self.assertEqual(first_quote.amount_out.amount, amount_out)

    def test_fixed_output_indirect_best_route(self):
        routes = [self.direct_route, self.indirect_route]

        amount_out = 10_000
        best_route = get_best_fixed_output_route(routes=routes, amount_out=amount_out)
        self.assertEqual(best_route, self.indirect_route)

        quotes = best_route.get_fixed_output_quotes(amount_out=amount_out)
        first_quote = quotes[0]
        self.assertEqual(first_quote.amount_in.amount, 40243)


class SwapRouterTransactionsTestCase(BaseTestCase):
    def test_prepare_swap_router_asset_opt_in_transaction(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        asset_ids = [1, 2, 3, 4]

        txn_group = prepare_swap_router_asset_opt_in_transaction(
            router_app_id=self.ROUTER_APP_ID,
            asset_ids=asset_ids,
            user_address=user_address,
            suggested_params=sp,
        )
        self.assertEqual(len(txn_group.transactions), 1)

        self.assertDictEqual(
            dict(txn_group.transactions[0].dictify()),
            {
                "apaa": [b"asset_opt_in"],
                "apan": OnComplete.NoOpOC,
                "apas": asset_ids,
                "apid": self.ROUTER_APP_ID,
                "fee": 1000 + len(asset_ids) * 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "appl",
            },
        )

    def test_fixed_input_prepare_swap_router_transactions(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        router_app_address = get_application_address(self.ROUTER_APP_ID)
        asset_in_amount = 1_000_000
        min_output = 2_000_000
        swap_type = "fixed-input"

        txn_group = prepare_swap_router_transactions(
            router_app_id=self.ROUTER_APP_ID,
            validator_app_id=self.VALIDATOR_APP_ID_V2,
            input_asset_id=self.asset_in.id,
            intermediary_asset_id=self.intermediary_asset.id,
            output_asset_id=self.asset_out.id,
            asset_in_amount=asset_in_amount,
            asset_out_amount=min_output,
            swap_type=swap_type,
            user_address=user_address,
            suggested_params=sp,
        )
        self.assertEqual(len(txn_group.transactions), 2)
        self.assertDictEqual(
            dict(txn_group.transactions[0].dictify()),
            {
                "aamt": 1000000,
                "arcv": decode_address(router_app_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "axfer",
                "xaid": self.asset_in.id,
            },
        )
        self.assertDictEqual(
            dict(txn_group.transactions[1].dictify()),
            {
                "apaa": [b"swap", b"fixed-input", min_output.to_bytes(8, "big")],
                "apan": OnComplete.NoOpOC,
                "apas": [
                    self.asset_in.id,
                    self.intermediary_asset.id,
                    self.asset_out.id,
                ],
                "apat": [
                    decode_address(self.pool_1.address),
                    decode_address(self.pool_2.address),
                ],
                "apfa": [self.VALIDATOR_APP_ID_V2],
                "apid": self.ROUTER_APP_ID,
                "fee": 8000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "appl",
            },
        )

    def test_output_input_prepare_swap_router_transactions(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        router_app_id = 99999
        router_app_address = get_application_address(router_app_id)
        asset_in_amount = 1_000_000
        asset_out_amount = 2_000_000
        swap_type = "fixed-output"

        txn_group = prepare_swap_router_transactions(
            router_app_id=router_app_id,
            validator_app_id=self.VALIDATOR_APP_ID_V2,
            input_asset_id=self.asset_in.id,
            intermediary_asset_id=self.intermediary_asset.id,
            output_asset_id=self.asset_out.id,
            asset_in_amount=asset_in_amount,
            asset_out_amount=asset_out_amount,
            swap_type=swap_type,
            user_address=user_address,
            suggested_params=sp,
        )
        self.assertEqual(len(txn_group.transactions), 2)
        self.assertDictEqual(
            dict(txn_group.transactions[0].dictify()),
            {
                "aamt": 1000000,
                "arcv": decode_address(router_app_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "axfer",
                "xaid": self.asset_in.id,
            },
        )
        self.assertDictEqual(
            dict(txn_group.transactions[1].dictify()),
            {
                "apaa": [b"swap", b"fixed-output", asset_out_amount.to_bytes(8, "big")],
                "apan": OnComplete.NoOpOC,
                "apas": [
                    self.asset_in.id,
                    self.intermediary_asset.id,
                    self.asset_out.id,
                ],
                "apat": [
                    decode_address(self.pool_1.address),
                    decode_address(self.pool_2.address),
                ],
                "apfa": [self.VALIDATOR_APP_ID_V2],
                "apid": router_app_id,
                "fee": 9000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "appl",
            },
        )

    def test_algo_input_prepare_swap_router_transactions(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        router_app_id = 99999
        router_app_address = get_application_address(router_app_id)
        asset_in_amount = 1_000_000
        min_output = 2_000_000
        swap_type = "fixed-input"

        txn_group = prepare_swap_router_transactions(
            router_app_id=router_app_id,
            validator_app_id=self.VALIDATOR_APP_ID_V2,
            input_asset_id=self.algo.id,
            intermediary_asset_id=self.intermediary_asset.id,
            output_asset_id=self.asset_out.id,
            asset_in_amount=asset_in_amount,
            asset_out_amount=min_output,
            swap_type=swap_type,
            user_address=user_address,
            suggested_params=sp,
        )
        self.assertEqual(len(txn_group.transactions), 2)
        # Pay instead of axfer
        self.assertDictEqual(
            dict(txn_group.transactions[0].dictify()),
            {
                "amt": 1000000,
                "rcv": decode_address(router_app_address),
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "snd": decode_address(user_address),
                "type": "pay",
            },
        )
        self.assertEqual(
            txn_group.transactions[1].dictify()["apas"],
            [self.algo.id, self.intermediary_asset.id, self.asset_out.id],
        )
        self.assertEqual(txn_group.transactions[1].dictify()["type"], "appl")

    def test_indirect_route_prepare_swap_router_transactions_from_quotes(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        asset_in = AssetAmount(self.asset_in, 1_000_000)
        asset_out = AssetAmount(self.asset_out, 2_000_000)
        asset_intermediary = AssetAmount(self.intermediary_asset, 9_999_999)
        swap_type = "fixed-input"

        route = Route(
            asset_in=self.asset_in,
            asset_out=self.asset_out,
            pools=[self.pool_1, self.pool_2],
        )

        quote_1 = V2SwapQuote(
            swap_type=swap_type,
            amount_in=asset_in,
            amount_out=asset_intermediary,
            swap_fees=None,
            slippage=0,
            price_impact=None,
        )
        quote_2 = V2SwapQuote(
            swap_type=swap_type,
            amount_in=asset_intermediary,
            amount_out=asset_out,
            swap_fees=None,
            slippage=0,
            price_impact=None,
        )
        quotes = [quote_1, quote_2]

        transfer_input_txn = {
            "aamt": asset_in.amount,
            "arcv": b"\xd4\xb4\xce\xaa\xc35V\xffg\xfa\xae\xcbz\xd0\x8a\xb3\x8f\x85\x1a\x9e\x06b\x8a\xf4X:\x0b\xae[\x93i\xde",
            "fee": ANY,
            "fv": ANY,
            "gh": ANY,
            "grp": ANY,
            "lv": ANY,
            "snd": decode_address(user_address),
            "type": "axfer",
            "xaid": self.asset_in.id,
        }
        swap_app_call_txn = {
            "apaa": [b"swap", b"fixed-input", asset_out.amount.to_bytes(8, "big")],
            "apan": OnComplete.NoOpOC,
            "apas": [self.asset_in.id, self.intermediary_asset.id, self.asset_out.id],
            "apat": [
                decode_address(self.pool_1.address),
                decode_address(self.pool_2.address),
            ],
            "apfa": [self.VALIDATOR_APP_ID_V2],
            "apid": self.ROUTER_APP_ID,
            "fee": ANY,
            "fv": ANY,
            "gh": ANY,
            "grp": ANY,
            "lv": ANY,
            "snd": decode_address(user_address),
            "type": "appl",
            "note": b'tinyman/v2:j{"origin":"tinyman-py-sdk"}',
        }

        txn_group = route.prepare_swap_router_transactions_from_quotes(
            quotes=quotes,
            user_address=user_address,
            suggested_params=sp,
        )
        self.assertEqual(len(txn_group.transactions), 2)
        self.assertDictEqual(
            dict(txn_group.transactions[0].dictify()), transfer_input_txn
        )
        self.assertDictEqual(
            dict(txn_group.transactions[1].dictify()), swap_app_call_txn
        )

    def test_swap_route_opt_in(self):
        sp = self.get_suggested_params()
        user_private_key, user_address = generate_account()
        router_app_address = get_application_address(self.ROUTER_APP_ID)
        algod = AlgodClient("TEST", "https://test.test.network")

        route = Route(
            asset_in=self.asset_in,
            asset_out=self.asset_out,
            pools=[self.pool_1, self.pool_2],
        )
        opt_in_app_call_txn = {
            "apaa": [b"asset_opt_in"],
            "apan": OnComplete.NoOpOC,
            "apas": ANY,
            "apid": self.ROUTER_APP_ID,
            "fee": ANY,
            "fv": ANY,
            "gh": ANY,
            "grp": ANY,
            "lv": ANY,
            "snd": decode_address(user_address),
            "type": "appl",
        }

        # 3 Opt-in
        account_info = self.get_mock_account_info(
            address=router_app_address,
            assets=[],
        )
        with patch(
            "algosdk.v2client.algod.AlgodClient.account_info", return_value=account_info
        ):
            opt_in_required_asset_ids = get_swap_router_app_opt_in_required_asset_ids(
                algod_client=algod,
                router_app_id=self.ROUTER_APP_ID,
                asset_ids=route.asset_ids,
            )
            self.assertEqual(opt_in_required_asset_ids, opt_in_app_call_txn["apas"])

            opt_in_txn_group = prepare_swap_router_asset_opt_in_transaction(
                router_app_id=self.ROUTER_APP_ID,
                asset_ids=opt_in_required_asset_ids,
                user_address=user_address,
                suggested_params=sp,
            )

            self.assertEqual(len(opt_in_txn_group.transactions), 1)
            self.assertDictEqual(
                dict(opt_in_txn_group.transactions[0].dictify()), opt_in_app_call_txn
            )

        # 2 Opt-in
        account_info = self.get_mock_account_info(
            address=router_app_address,
            assets=[
                {"amount": 0, "asset-id": self.asset_in.id, "is-frozen": False},
            ],
        )
        with patch(
            "algosdk.v2client.algod.AlgodClient.account_info", return_value=account_info
        ):
            opt_in_app_call_txn["apas"] = [
                self.asset_out.id,
                self.intermediary_asset.id,
            ]
            opt_in_app_call_txn["fee"] = 3 * 1000

            opt_in_required_asset_ids = get_swap_router_app_opt_in_required_asset_ids(
                algod_client=algod,
                router_app_id=self.ROUTER_APP_ID,
                asset_ids=route.asset_ids,
            )
            self.assertEqual(opt_in_required_asset_ids, opt_in_app_call_txn["apas"])

            opt_in_txn_group = prepare_swap_router_asset_opt_in_transaction(
                router_app_id=self.ROUTER_APP_ID,
                asset_ids=opt_in_required_asset_ids,
                user_address=user_address,
                suggested_params=sp,
            )

            self.assertEqual(len(opt_in_txn_group.transactions), 1)
            self.assertDictEqual(
                dict(opt_in_txn_group.transactions[0].dictify()), opt_in_app_call_txn
            )

        # No opt-in + Slippage
        account_info = self.get_mock_account_info(
            address=router_app_address,
            assets=[
                {"amount": 0, "asset-id": self.asset_in.id, "is-frozen": False},
                {
                    "amount": 0,
                    "asset-id": self.intermediary_asset.id,
                    "is-frozen": False,
                },
                {"amount": 0, "asset-id": self.asset_out.id, "is-frozen": False},
            ],
        )
        with patch(
            "algosdk.v2client.algod.AlgodClient.account_info", return_value=account_info
        ):
            opt_in_required_asset_ids = get_swap_router_app_opt_in_required_asset_ids(
                algod_client=algod,
                router_app_id=self.ROUTER_APP_ID,
                asset_ids=route.asset_ids,
            )
            self.assertEqual(opt_in_required_asset_ids, [])


class EventLogParserTestCase(TestCase):
    def test_bytes_log(self):
        raw_log = b"\x81b\xda\x9e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x00\x00\x00\x00&\xbb"
        result = parse_swap_router_event_log(log=raw_log)
        self.assertDictEqual(
            result,
            {
                "input_asset_id": 0,
                "output_asset_id": 5,
                "input_amount": 1000,
                "output_amount": 9915,
            },
        )

    def test_string_log(self):
        raw_log = "gWLangAAAAAAn5c9AAAAAAQwcrUAAAAAAAGGoAAAAAAAA5u2"
        result = parse_swap_router_event_log(log=raw_log)
        self.assertDictEqual(
            result,
            {
                "input_asset_id": 10458941,
                "output_asset_id": 70283957,
                "input_amount": 100000,
                "output_amount": 236470,
            },
        )

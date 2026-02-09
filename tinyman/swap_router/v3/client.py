import requests
from typing import List

from algosdk import transaction
from algosdk.encoding import decode_address, encode_address

from tinyman.swap_router.base_client import BaseClient
from tinyman.swap_router.v3.utils import parse_quotes_v3_response
from tinyman.v2.constants import MAINNET_VALIDATOR_APP_ID_V2, TESTNET_VALIDATOR_APP_ID_V2
from tinyman.liquid_staking.constants import MAINNET_TALGO_APP_ID, MAINNET_TALGO_ASSET_ID, TESTNET_TALGO_APP_ID, TESTNET_TALGO_ASSET_ID
from tinyman.swap_router.constants import MAINNET_SWAP_ROUTER_V3_APP_ID, TESTNET_SWAP_ROUTER_V3_APP_ID


class SwapRouterClient(BaseClient):
    def __init__(self, algod, base_url, app_id, tinyman_amm_app_id, talgo_app_id, user_address, user_sk, talgo_asset_id: int = None, talgo_app_accounts: List[str] = None) -> None:
        super().__init__(algod, app_id, user_address, user_sk)
        self.base_url = base_url
        self.amm_app_id = tinyman_amm_app_id
        self.talgo_app_id = talgo_app_id

        if talgo_asset_id is None or talgo_app_accounts is None:
            state = self.get_globals(talgo_app_id)
            self.talgo_asset_id = state[b"talgo_asset_id"]
            self.talgo_app_address = encode_address(state[b"account_0"])
            self.talgo_app_accounts = [encode_address(state[b"account_%i" % i]) for i in range(5)]
        else:
            assert len(talgo_app_accounts) == 5
            self.talgo_app_accounts = talgo_app_accounts
            self.talgo_asset_id = talgo_asset_id

    def get_swap_quote(self, input_asset_id, output_asset_id, swap_amount, swap_type='fixed-input', slippage=0.005):
        payload = {"input_asset_id": input_asset_id, "output_asset_id": output_asset_id, "swap_type": swap_type, "slippage": slippage}

        if swap_type == 'fixed-input':
            payload['input_amount'] = swap_amount
        elif swap_type == 'fixed-output':
            payload['output_amount'] = swap_amount
        else:
            raise NotImplementedError()

        response = requests.post(f"{self.base_url}/api/v1/swap-router/quotes-v3/", payload)
        return parse_quotes_v3_response(response.json())

    def execute_quote(self, quote):
        asset_mapping = quote['asset_mapping']
        transaction_parameters = quote['transaction_parameters']
        app_asset_optins = []

        for route in asset_mapping:
            app_asset_optins.extend([aid for aid in route if aid and not self.is_opted_in(self.application_address, aid)])

        transactions = [
            self.get_optin_if_needed_txn(self.user_address, asset_mapping[0][-1])
        ]

        sp = self.get_suggested_params()
        transactions.extend(self.get_transactions_from_parameters(transaction_parameters, sp))

        inner_txns = sum(params.get("inner_txns", 0) for params in transaction_parameters)
        return self._submit(transactions, additional_fees=inner_txns)

    def get_transactions_from_parameters(self, transaction_parameters, sp=None):
        if sp is None:
            sp = self.get_suggested_params()

        transactions = []
        for params in transaction_parameters:
            if params["type"] == "pay":
                transactions.append(transaction.PaymentTxn(
                    sender=self.user_address,
                    sp=sp,
                    receiver=params["receiver"],
                    amt=params["amount"],
                ))
            elif params["type"] == "axfer":
                transactions.append(transaction.AssetTransferTxn(
                    sender=self.user_address,
                    sp=sp,
                    receiver=params["receiver"],
                    amt=params["amount"],
                    index=params["asset_id"],
                ))
            elif params["type"] == "appl":
                transactions.append(transaction.ApplicationNoOpTxn(
                    sender=self.user_address,
                    sp=sp,
                    index=params["app_id"],
                    app_args=params["args"],
                    accounts=params.get("accounts"),
                    foreign_assets=params.get("assets"),
                    foreign_apps=params.get("apps"),
                ))

        return transactions


class SwapRouterManagerClient:
    def claim_extra(self, asset_id):
        sp = self.get_suggested_params()
        txns = [
            transaction.ApplicationNoOpTxn(
                sender=self.user_address,
                sp=sp,
                index=self.app_id,
                app_args=[b"claim_extra", asset_id],
                foreign_assets=[asset_id],
            )
        ]
        return self._submit(txns, additional_fees=1)

    def set_extra_collector(self, new_collector):
        sp = self.get_suggested_params()
        txns = [
            transaction.ApplicationNoOpTxn(
                sender=self.user_address,
                sp=sp,
                index=self.app_id,
                app_args=[b"set_extra_collector", decode_address(new_collector)],
            )
        ]
        return self._submit(txns, additional_fees=0)

    def propose_manager(self, new_manager):
        sp = self.get_suggested_params()
        txns = [
            transaction.ApplicationNoOpTxn(
                sender=self.user_address,
                sp=sp,
                index=self.app_id,
                app_args=[b"propose_manager", decode_address(new_manager)],
            )
        ]
        return self._submit(txns, additional_fees=0)

    def accept_manager(self):
        sp = self.get_suggested_params()
        txns = [
            transaction.ApplicationNoOpTxn(
                sender=self.user_address,
                sp=sp,
                index=self.app_id,
                app_args=[b"accept_manager"],
            )
        ]
        return self._submit(txns, additional_fees=0)


class MainnetSwapRouterClient(SwapRouterClient):
    def __init__(self, algod, user_address, user_sk):
        super().__init__(
            algod=algod,
            base_url="https://mainnet.analytics.tinyman.org",
            app_id=MAINNET_SWAP_ROUTER_V3_APP_ID,
            tinyman_amm_app_id=MAINNET_VALIDATOR_APP_ID_V2,
            talgo_app_id=MAINNET_TALGO_APP_ID,
            talgo_asset_id=MAINNET_TALGO_ASSET_ID,
            user_address=user_address,
            user_sk=user_sk
        )


class TestnetSwapRouterClient(SwapRouterClient):
    def __init__(self, algod, user_address, user_sk):
        super().__init__(
            algod=algod,
            base_url="https://testnet.analytics.tinyman.org",
            app_id=TESTNET_SWAP_ROUTER_V3_APP_ID,
            tinyman_amm_app_id=TESTNET_VALIDATOR_APP_ID_V2,
            talgo_app_id=TESTNET_TALGO_APP_ID,
            talgo_asset_id=TESTNET_TALGO_ASSET_ID,
            user_address=user_address,
            user_sk=user_sk
        )

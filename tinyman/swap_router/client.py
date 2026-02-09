from algosdk import transaction
from algosdk.logic import get_application_address
from typing import List

from .base_client import BaseClient
from .utils import group_references, int_array, encode_router_args


class SwapRouterClient(BaseClient):

    def __init__(self, algod, app_id, tinyman_amm_app_id, talgo_app_id, talgo_asset_id, talgo_app_accounts: List[str], user_address, user_sk) -> None:
        super().__init__(algod, app_id, user_address, user_sk)
        self.amm_app_id = tinyman_amm_app_id
        self.talgo_app_id = talgo_app_id
        self.talgo_app_address = get_application_address(talgo_app_id)
        self.talgo_asset_id = talgo_asset_id
        self.talgo_app_accounts = talgo_app_accounts

    def get_swap_txns_parameters(self, input_amount, output_amount, route, pools, app_asset_optins=[]):
        """
        route: List[int]; asset-ids.
        pools: List[str]; pool addresses.
        """

        input_asset_id = route[0]

        route_arg, pools_arg = encode_router_args(route, pools)
        swaps = len(pools)

        assert len(route) == (swaps + 1), "Invalid route."

        grouped_references = group_references(route, pools, self.amm_app_id, self.talgo_asset_id, self.talgo_app_id, self.talgo_app_accounts)

        transactions = []

        if app_asset_optins:
            transactions.append(
                dict(
                    type="appl",
                    app_id=self.app_id,
                    args=["asset_opt_in", int_array(app_asset_optins, 8, 0)],
                    apps=[self.amm_app_id],
                    assets=app_asset_optins,
                    inner_txns=len(app_asset_optins),
                )
            )

        transactions += [
            dict(
                type="axfer" if input_asset_id else "pay",
                receiver=self.application_address,
                amount=input_amount,
                asset_id=input_asset_id,
            ),
            dict(
                type="appl",
                app_id=self.app_id,
                args=["swap", input_amount, output_amount, route_arg, pools_arg, swaps],
                apps=grouped_references[0]["apps"],
                accounts=grouped_references[0]["accounts"],
                assets=grouped_references[0]["assets"],
                inner_txns=(swaps * 3) + 1,
            ),
        ]
        for refs in grouped_references[1:]:
            transactions.append(
                dict(
                    type="appl",
                    app_id=self.app_id,
                    args=["noop"],
                    apps=refs["apps"],
                    accounts=refs["accounts"],
                    assets=refs["assets"],
                )
            )

        return transactions

    def swap(self, input_amount, output_amount, route, pools):
        optins = [a for a in route if a and not self.is_opted_in(self.application_address, a)]
        transactions = self.get_swap_txns_parameters(input_amount, output_amount, route, pools, optins)

        sp = self.get_suggested_params()
        txns = [
            self.get_optin_if_needed_txn(self.user_address, route[-1])
        ]

        for tx in transactions:
            if tx["type"] == "pay":
                txns.append(transaction.PaymentTxn(
                    sender=self.user_address,
                    sp=sp,
                    receiver=tx["receiver"],
                    amt=tx["amount"],
                ))
            elif tx["type"] == "axfer":
                txns.append(transaction.AssetTransferTxn(
                    sender=self.user_address,
                    sp=sp,
                    receiver=tx["receiver"],
                    amt=tx["amount"],
                    index=tx["asset_id"],
                ))
            elif tx["type"] == "appl":
                txns.append(transaction.ApplicationNoOpTxn(
                    sender=self.user_address,
                    sp=sp,
                    index=tx["app_id"],
                    app_args=tx["args"],
                    accounts=tx.get("accounts"),
                    foreign_assets=tx.get("assets"),
                    foreign_apps=tx.get("apps"),
                ))
        inner_txns = sum(tx.get("inner_txns", 0) for tx in transactions)

        return self._submit(txns, additional_fees=inner_txns)

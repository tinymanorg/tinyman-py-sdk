from algosdk.encoding import decode_address
from algosdk.logic import get_application_address
from algosdk.constants import ZERO_ADDRESS
from base64 import b64decode
from collections import defaultdict
from typing import List, Tuple

from tinyman.utils import int_to_bytes
from tinyman.swap_router.utils import int_array, bytes_array


def decode_transaction_parameters(transaction_parameters):
    "For decoding the API response."
    for tx in transaction_parameters:
        if tx['type'] == "appl":
            args = [b64decode(x) for x in tx.get("args")]
            tx['args'] = args

    return transaction_parameters


def prepare_swap_group_transaction_parameters(
    self,
    input_asset_id,
    output_asset_id,
    input_amount_mapping,
    output_amount,
    asset_mapping,
    pool_mapping,
    app_asset_optins=[]
):

    transaction_dicts = []
    inner_transaction_count = 0

    total_input_amount = sum(input_amount_mapping)

    # Prepare app asset opt-in transactions.
    assert len(app_asset_optins) <= 8
    if app_asset_optins:
        transaction_dicts.append(
            dict(
                type="appl",
                app_id=self.app_id,
                args=["asset_opt_in", int_array(app_asset_optins, 8, 0)],
                apps=[self.amm_app_id],
                assets=app_asset_optins,
                inner_txns=len(app_asset_optins),
            )
        )
        inner_transaction_count += len(app_asset_optins)

    # Prepare Axfer/Pay
    transaction_dicts.append(
        dict(
            type="axfer" if input_asset_id else "pay",
            receiver=self.application_address,
            amount=total_input_amount,
            asset_id=input_asset_id,
        ),
    )

    # For each route, group (input_asset, output_asset, pool)
    is_talgo_app_used = False
    talgo_app_address = get_application_address(self.talgo_app_id)

    swap_pair_pool_mapping: List[List[Tuple[int, int, str]]] = []
    for route, pool_addresses in zip(asset_mapping, pool_mapping):
        pair_pool_mapping = []
        for index in range(len(pool_addresses)):
            pool_address = pool_addresses[index]
            input_asset = route[index]
            output_asset = route[index + 1]

            if pool_address == talgo_app_address:
                is_talgo_app_used = True
                continue

            pair_pool_mapping.append((input_asset, output_asset, pool_address))
        swap_pair_pool_mapping.append(pair_pool_mapping)

    ref_groups = []
    for pair_pool_mapping in swap_pair_pool_mapping:
        ref_group = []
        for index in range(0, len(pair_pool_mapping), 2):
            refs = defaultdict(lambda: [])
            for input_asset, output_asset, pool_address in pair_pool_mapping[index: index + 2]:
                refs['accounts'].append(pool_address)
                refs['assets'].append(input_asset)
                refs['assets'].append(output_asset)
            refs["assets"] = list(set(refs["assets"]))  # Remove duplicate intermediary asset.
            ref_group.append(refs)
        ref_groups.append(ref_group)

    swap_txn_dicts = []
    # Prepare `swap` transactions.
    for route, pool_addresses, input_amount, ref_group in zip(asset_mapping, pool_mapping, input_amount_mapping, ref_groups):
        route_arg = int_array(elements=route, size=8, default=0)
        pools_arg = bytes_array(elements=[decode_address(addr) for addr in pool_addresses], size=8, default=decode_address(ZERO_ADDRESS))
        swaps = len(pool_addresses)

        swap_txn_dict = dict(
            type="appl",
            app_id=self.app_id,
            args=["swap", input_amount, route_arg, pools_arg, swaps],
            apps=[self.amm_app_id],
            accounts=ref_group[0]["accounts"],
            assets=ref_group[0]["assets"],
            inner_txns=(swaps * 3) + 1,
        )

        inner_transaction_count += (swaps * 3) + 1
        swap_txn_dicts.append(swap_txn_dict)

        for refs in ref_group[1:]:
            swap_txn_dicts.append(
                dict(
                    type="appl",
                    app_id=self.app_id,
                    args=["noop"],
                    apps=[self.amm_app_id],
                    accounts=refs["accounts"],
                    assets=refs["assets"],
                )
            )

    if is_talgo_app_used:
        swap_txn_dicts.append(
            dict(
                type="appl",
                app_id=self.app_id,
                args=["noop"],
                apps=[self.amm_app_id, self.talgo_app_id],
                accounts=self.talgo_app_accounts[1:],
                assets=[self.talgo_asset_id]
            )
        )

    # Prepare `start_swap_group` transaction.
    index_diff = len(swap_txn_dicts) + 1

    transaction_dicts.append(
        dict(
            type="appl",
            app_id=self.app_id,
            args=[
                "start_swap_group",
                int_to_bytes(input_asset_id),
                int_to_bytes(output_asset_id),
                int_to_bytes(total_input_amount),
                int_to_bytes(index_diff)
            ],
            assets=[output_asset_id]
        )
    )
    transaction_dicts.extend(swap_txn_dicts)

    # Prepare `end_swap_group` transaction.
    transaction_dicts.append(
        dict(
            type="appl",
            app_id=self.app_id,
            args=[
                "end_swap_group",
                int_to_bytes(input_asset_id),
                int_to_bytes(output_asset_id),
                int_to_bytes(total_input_amount),
                int_to_bytes(output_amount),
                int_to_bytes(index_diff)
            ],
            assets=[output_asset_id]
        )
    )

    return transaction_dicts


def parse_quotes_v3_response(rjson: dict) -> dict:
    result = dict()

    result['transaction_parameters'] = decode_transaction_parameters(rjson['transactions'])
    result['input_amount_mapping'] = [int(iamt) for iamt in rjson['input_amount_mapping']]
    result['input_asset_id'] = int(rjson['input_asset']['id'])
    result['output_asset_id'] = int(rjson['output_asset']['id'])
    result['output_amount'] = int(rjson['output_amount'])
    result['asset_mapping'] = rjson['asset_mapping']
    result['pool_mapping'] = rjson['pool_mapping']

    return result

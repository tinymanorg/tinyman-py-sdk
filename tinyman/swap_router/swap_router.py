from typing import Optional

import requests
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient

from tinyman.assets import Asset
from tinyman.compat import (
    AssetTransferTxn,
    ApplicationNoOpTxn,
    SuggestedParams,
    PaymentTxn,
)
from tinyman.swap_router.constants import (
    FIXED_INPUT_SWAP_TYPE,
    FIXED_OUTPUT_SWAP_TYPE,
)
from tinyman.swap_router.routes import Route
from tinyman.utils import TransactionGroup
from tinyman.v2.client import TinymanV2Client
from tinyman.v2.constants import FIXED_INPUT_APP_ARGUMENT, FIXED_OUTPUT_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool as TinymanV2Pool


def prepare_swap_router_asset_opt_in_transaction(
    router_app_id: int,
    asset_ids: [int],
    user_address: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:

    asset_opt_in_app_call = ApplicationNoOpTxn(
        sender=user_address,
        sp=suggested_params,
        index=router_app_id,
        app_args=["asset_opt_in"],
        foreign_assets=asset_ids,
    )
    min_fee = suggested_params.min_fee
    inner_transaction_count = len(asset_ids)
    asset_opt_in_app_call.fee = min_fee * (1 + inner_transaction_count)

    txn_group = TransactionGroup([asset_opt_in_app_call])
    return txn_group


def prepare_swap_router_transactions(
    router_app_id: int,
    validator_app_id: int,
    input_asset_id: int,
    intermediary_asset_id: int,
    output_asset_id: int,
    asset_in_amount: int,
    asset_out_amount: int,
    swap_type: [str, bytes],
    user_address: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    pool_1_logicsig = get_pool_logicsig(
        validator_app_id, input_asset_id, intermediary_asset_id
    )
    pool_1_address = pool_1_logicsig.address()

    pool_2_logicsig = get_pool_logicsig(
        validator_app_id, intermediary_asset_id, output_asset_id
    )
    pool_2_address = pool_2_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=user_address,
            sp=suggested_params,
            receiver=get_application_address(router_app_id),
            index=input_asset_id,
            amt=asset_in_amount,
        )
        if input_asset_id != 0
        else PaymentTxn(
            sender=user_address,
            sp=suggested_params,
            receiver=get_application_address(router_app_id),
            amt=asset_in_amount,
        ),
        ApplicationNoOpTxn(
            sender=user_address,
            sp=suggested_params,
            index=router_app_id,
            app_args=["swap", swap_type, asset_out_amount],
            accounts=[pool_1_address, pool_2_address],
            foreign_apps=[validator_app_id],
            foreign_assets=[input_asset_id, intermediary_asset_id, output_asset_id],
            note=app_call_note,
        ),
    ]

    if isinstance(swap_type, bytes):
        pass
    elif isinstance(swap_type, str):
        swap_type = swap_type.encode()
    else:
        raise NotImplementedError()

    min_fee = suggested_params.min_fee
    if swap_type == FIXED_INPUT_APP_ARGUMENT:
        inner_transaction_count = 7
        app_call_fee = min_fee * (1 + inner_transaction_count)
    elif swap_type == FIXED_OUTPUT_APP_ARGUMENT:
        inner_transaction_count = 8
        app_call_fee = min_fee * (1 + inner_transaction_count)
    else:
        raise NotImplementedError()

    txns[-1].fee = app_call_fee
    txn_group = TransactionGroup(txns)
    return txn_group


def get_swap_router_app_opt_in_required_asset_ids(
    algod_client: AlgodClient, router_app_id: int, asset_ids=list[int]
) -> list[int]:
    swap_router_app_address = get_application_address(router_app_id)
    account_info = algod_client.account_info(swap_router_app_address)

    app_opted_in_asset_ids = {
        int(asset["asset-id"]) for asset in account_info["assets"]
    }

    app_opt_in_required_asset_ids = list(set(asset_ids) - {0} - app_opted_in_asset_ids)
    return app_opt_in_required_asset_ids


def fetch_best_route_suggestion(
    tinyman_client: TinymanV2Client,
    asset_in: Asset,
    asset_out: Asset,
    swap_type: str,
    amount: int,
) -> Route:
    assert swap_type in (FIXED_INPUT_SWAP_TYPE, FIXED_OUTPUT_SWAP_TYPE)
    assert amount > 0

    payload = {
        "asset_in_id": str(asset_in.id),
        "asset_out_id": str(asset_out.id),
        "swap_type": swap_type,
        "amount": str(amount),
    }

    r = requests.post(
        tinyman_client.api_base_url + "v1/swap-router/quotes/", json=payload
    )
    r.raise_for_status()
    response = r.json()

    pools = []
    for quote in response["route"]:
        pool = TinymanV2Pool(
            client=tinyman_client,
            asset_a=Asset(
                id=int(quote["pool"]["asset_1"]["id"]),
                name=quote["pool"]["asset_1"]["name"],
                unit_name=quote["pool"]["asset_1"]["unit_name"],
                decimals=quote["pool"]["asset_1"]["decimals"],
            ),
            asset_b=Asset(
                id=int(quote["pool"]["asset_2"]["id"]),
                name=quote["pool"]["asset_2"]["name"],
                unit_name=quote["pool"]["asset_2"]["unit_name"],
                decimals=quote["pool"]["asset_2"]["decimals"],
            ),
            fetch=True,
        )
        pools.append(pool)

    route = Route(asset_in=asset_in, asset_out=asset_out, pools=pools)
    return route

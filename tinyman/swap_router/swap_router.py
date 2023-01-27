from typing import Union

from algosdk.future.transaction import (
    AssetTransferTxn,
    ApplicationNoOpTxn,
    SuggestedParams,
    PaymentTxn,
)
from algosdk.logic import get_application_address
from requests import request, HTTPError

from tinyman.assets import AssetAmount
from tinyman.swap_router.constants import (
    FIXED_INPUT_SWAP_TYPE,
    FIXED_OUTPUT_SWAP_TYPE,
)
from tinyman.utils import TransactionGroup
from tinyman.v1.client import TinymanClient
from tinyman.v1.pools import Pool as TinymanV1Pool, SwapQuote as TinymanV1SwapQuote
from tinyman.v2.client import TinymanV2Client
from tinyman.v2.constants import FIXED_INPUT_APP_ARGUMENT, FIXED_OUTPUT_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool as TinymanV2Pool
from tinyman.v2.quotes import SwapQuote as TinymanV2SwapQuote


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


def prepare_swap_router_transactions_from_quotes(
    route_pools_and_quotes: list[
        Union[
            tuple[TinymanV1Pool, TinymanV1SwapQuote],
            tuple[TinymanV2Pool, TinymanV2SwapQuote],
        ]
    ],
    swap_type: str,
    slippage: float = 0.05,
    user_address: str = None,
    suggested_params: SuggestedParams = None,
) -> TransactionGroup:
    # override slippage
    for i in range(len(route_pools_and_quotes)):
        route_pools_and_quotes[i][1].slippage = slippage

    swap_count = len(route_pools_and_quotes)
    if swap_count == 1:
        pool, quote = route_pools_and_quotes[0]
        quote.slippage = slippage

        if isinstance(pool, TinymanV1Pool):
            return pool.prepare_swap_transactions_from_quote(
                quote=quote,
                swapper_address=user_address,
                # suggested_params=suggested_params,
            )
        elif isinstance(pool, TinymanV2Pool):
            return pool.prepare_swap_transactions_from_quote(
                quote=quote,
                user_address=user_address,
                suggested_params=suggested_params,
            )
        else:
            raise NotImplementedError()

    elif swap_count == 2:
        pools, quotes = zip(*route_pools_and_quotes)
        router_app_id = pools[0].client.router_app_id
        validator_app_id = pools[0].client.validator_app_id

        input_asset_id = quotes[0].amount_in.asset.id
        intermediary_asset_id = quotes[0].amount_out.asset.id
        output_asset_id = quotes[-1].amount_out.asset.id

        txn_group = prepare_swap_router_transactions(
            router_app_id=router_app_id,
            validator_app_id=validator_app_id,
            input_asset_id=input_asset_id,
            intermediary_asset_id=intermediary_asset_id,
            output_asset_id=output_asset_id,
            asset_in_amount=quotes[0].amount_in_with_slippage.amount,
            asset_out_amount=quotes[-1].amount_out_with_slippage.amount,
            swap_type=swap_type,
            user_address=user_address,
            suggested_params=suggested_params,
        )

        algod_client = pools[0].client.algod_client
        swap_router_app_address = get_application_address(router_app_id)
        account_info = algod_client.account_info(swap_router_app_address)
        opted_in_asset_ids = {
            int(asset["asset-id"]) for asset in account_info["assets"]
        }
        asset_ids = (
            {input_asset_id, intermediary_asset_id, output_asset_id}
            - {0}
            - opted_in_asset_ids
        )

        if asset_ids:
            opt_in_txn_group = prepare_swap_router_asset_opt_in_transaction(
                router_app_id=router_app_id,
                asset_ids=list(asset_ids),
                user_address=user_address,
                suggested_params=suggested_params,
            )
            txn_group = opt_in_txn_group + txn_group

        return txn_group

    else:
        raise NotImplementedError()


def fetch_swap_route_quotes(
    tinyman_v1_client: TinymanClient,
    tinyman_v2_client: TinymanV2Client,
    asset_in_id: int,
    asset_out_id: int,
    swap_type: str,
    amount: int,
) -> list[
    Union[
        tuple[TinymanV1Pool, TinymanV1SwapQuote],
        tuple[TinymanV2Pool, TinymanV2SwapQuote],
    ]
]:
    assert swap_type in (FIXED_INPUT_SWAP_TYPE, FIXED_OUTPUT_SWAP_TYPE)
    assert amount > 0
    assert asset_in_id >= 0
    assert asset_out_id >= 0
    assert isinstance(tinyman_v1_client, TinymanClient)
    assert isinstance(tinyman_v2_client, TinymanV2Client)

    payload = {
        "asset_in_id": str(asset_in_id),
        "asset_out_id": str(asset_out_id),
        "swap_type": swap_type,
        "amount": str(amount),
    }

    raw_response = request(
        method="POST",
        url="http://dev.analytics.tinyman.org/api/v1/swap-router/",
        # TODO: url=client.api_base_url + "v1/swap-router/", "v1/swap-router/quotes/",
        json=payload,
    )

    # TODO: Handle all errors properly.
    if raw_response.status_code != 200:
        raise HTTPError(response=raw_response)

    response = raw_response.json()
    print(response)

    route_pools_and_quotes = []
    for swap in response["route"]:
        if swap["pool"]["version"] == "1.1":
            client = tinyman_v1_client
            pool = TinymanV1Pool(
                client=client,
                asset_a=client.fetch_asset(int(swap["pool"]["asset_1_id"])),
                asset_b=client.fetch_asset(int(swap["pool"]["asset_2_id"])),
                fetch=True,
            )

            asset_in = client.fetch_asset(int(swap["quote"]["amount_in"]["asset_id"]))
            amount_out = client.fetch_asset(
                int(swap["quote"]["amount_out"]["asset_id"])
            )

            quote = TinymanV1SwapQuote(
                swap_type=swap_type,
                amount_in=AssetAmount(
                    asset_in, int(swap["quote"]["amount_in"]["amount"])
                ),
                amount_out=AssetAmount(
                    amount_out, int(swap["quote"]["amount_out"]["amount"])
                ),
                swap_fees=AssetAmount(
                    asset_in, int(swap["quote"]["amount_in"]["amount"])
                ),
                slippage=0,
                price_impact=swap["quote"]["price_impact"],
            )

        elif swap["pool"]["version"] == "2.0":
            client = tinyman_v2_client

            pool = TinymanV2Pool(
                client=client,
                asset_a=client.fetch_asset(int(swap["pool"]["asset_1_id"])),
                asset_b=client.fetch_asset(int(swap["pool"]["asset_2_id"])),
                fetch=True,
            )

            asset_in = client.fetch_asset(int(swap["quote"]["amount_in"]["asset_id"]))
            amount_out = client.fetch_asset(
                int(swap["quote"]["amount_out"]["asset_id"])
            )

            quote = TinymanV2SwapQuote(
                swap_type=swap_type,
                amount_in=AssetAmount(
                    asset_in, int(swap["quote"]["amount_in"]["amount"])
                ),
                amount_out=AssetAmount(
                    amount_out, int(swap["quote"]["amount_out"]["amount"])
                ),
                swap_fees=AssetAmount(
                    asset_in, int(swap["quote"]["amount_in"]["amount"])
                ),
                slippage=0,
                price_impact=swap["quote"]["price_impact"],
            )
        else:
            raise NotImplementedError()
        route_pools_and_quotes.append((pool, quote))

    return route_pools_and_quotes


# def fetch_best_route(
#     tinyman_v1_client: TinymanClient,
#     tinyman_v2_client: TinymanV2Client,
#     asset_in_id: int,
#     asset_out_id: int,
#     swap_type: str,
#     amount: int,
# ):
#     asset_in = tinyman_v2_client.fetch_asset(asset_in_id)
#     asset_out = tinyman_v2_client.fetch_asset(asset_out_id)
#     routes = []
#
#     v1_pool = TinymanV1Pool(
#         client=tinyman_v1_client,
#         asset_a=asset_in,
#         asset_b=asset_out,
#         fetch=True,
#     )
#     if v1_pool.exists:
#         direct_v1_route = Route(asset_in=asset_in, asset_out=asset_out, pools=[v1_pool])
#         routes.append(direct_v1_route)
#
#     v2_pool = TinymanV2Pool(
#         client=tinyman_v2_client,
#         asset_a=asset_in,
#         asset_b=asset_out,
#         fetch=True,
#     )
#     if v2_pool.exists:
#         direct_v2_route = Route(asset_in=asset_in, asset_out=asset_out, pools=[v2_pool])
#         routes.append(direct_v2_route)
#
#     try:
#         smart_route = fetch_swap_route(
#             tinyman_v1_client=tinyman_v1_client,
#             tinyman_v2_client=tinyman_v2_client,
#             asset_in_id=asset_in_id,
#             asset_out_id=asset_out_id,
#             swap_type=swap_type,
#             amount=amount,
#         )
#     except Exception:  # TODO: Handle the exception properly.
#         smart_swap_route = None
#
#     if smart_swap_route is not None:
#         routes.append(smart_swap_route)
#
#     if swap_type == FIXED_INPUT_SWAP_TYPE:
#         best_route = get_best_fixed_input_route(routes=routes, amount_in=amount)
#     elif swap_type == FIXED_OUTPUT_SWAP_TYPE:
#         best_route = get_best_fixed_output_route(routes=routes, amount_out=amount)
#     else:
#         raise NotImplementedError()
#
#     return best_route

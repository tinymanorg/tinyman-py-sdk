from algosdk.future.transaction import (
    AssetTransferTxn,
    ApplicationNoOpTxn,
    SuggestedParams,
    PaymentTxn,
)
from algosdk.logic import get_application_address
from requests import request, HTTPError

from tinyman.swap_router.constants import (
    FIXED_INPUT_SWAP_TYPE,
    FIXED_OUTPUT_SWAP_TYPE,
    TESTNET_SWAP_ROUTER_APP_ID_V1,
)
from tinyman.swap_router.routes import Route
from tinyman.swap_router.utils import (
    get_best_fixed_input_route,
    get_best_fixed_output_route,
)
from tinyman.utils import TransactionGroup
from tinyman.v1.client import TinymanClient
from tinyman.v1.pools import Pool as TinymanV1Pool
from tinyman.v2.client import TinymanV2Client
from tinyman.v2.constants import FIXED_INPUT_APP_ARGUMENT, FIXED_OUTPUT_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool as TinymanV2Pool


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
    # TODO: MVP
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
        app_call_fee = min_fee * 8
    elif swap_type == FIXED_OUTPUT_APP_ARGUMENT:
        app_call_fee = min_fee * 9
    else:
        raise NotImplementedError()

    txns[-1].fee = app_call_fee
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_transactions(
    route: Route,
    swap_type: str,
    amount: int,
    slippage: float = 0.05,
    user_address: str = None,
    suggested_params: SuggestedParams = None,
):
    if swap_type == FIXED_INPUT_SWAP_TYPE:
        quotes = route.get_fixed_input_quotes(amount_in=amount, slippage=slippage)
    elif swap_type == FIXED_OUTPUT_SWAP_TYPE:
        quotes = route.get_fixed_output_quotes(amount_out=amount, slippage=slippage)
    else:
        raise NotImplementedError()

    swap_count = len(route.pools)
    if swap_count == 1:
        pool = route.pools[0]
        quote = quotes[0]

        if isinstance(pool, TinymanV1Pool):
            return pool.prepare_swap_transactions_from_quote(
                quote=quote,
                swapper_address=user_address,
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
        if quotes[0].amount_in.asset.id == route.asset_in.id:
            intermediary_asset_id = quotes[0].amount_out.asset.id
        else:
            intermediary_asset_id = quotes[0].amount_in.asset.id

        prepare_swap_router_transactions(
            # TODO: Add router_app_id to client.
            router_app_id=TESTNET_SWAP_ROUTER_APP_ID_V1,
            validator_app_id=TinymanV2Client.validator_app_id,
            input_asset_id=route.asset_in.id,
            intermediary_asset_id=intermediary_asset_id,
            output_asset_id=route.asset_out.id,
            asset_in_amount=quotes[0].amount_in_with_slippage,
            asset_out_amount=quotes[-1].amount_out_with_slippage,
            swap_type=swap_type,
            user_address=user_address,
            suggested_params=suggested_params,
        )

    else:
        raise NotImplementedError()


def fetch_smart_swap_route(
    tinyman_v1_client: TinymanClient,
    tinyman_v2_client: TinymanV2Client,
    asset_in_id: int,
    asset_out_id: int,
    swap_type: str,
    amount: int,
):
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
        # url=client.api_base_url + "v1/swap-router/",
        json=payload,
    )

    # TODO: Handle all errors properly.
    if raw_response.status_code != 200:
        raise HTTPError(response=raw_response)

    response = raw_response.json()
    print(response)

    pools = []
    for swap in response["route"]:
        if swap["pool"]["version"] == "1.1":
            pool = TinymanV1Pool(
                client=tinyman_v1_client,
                asset_a=swap["pool"]["asset_1_id"],
                asset_b=swap["pool"]["asset_2_id"],
                fetch=True,
            )
        elif swap["pool"]["version"] == "2.0":
            pool = TinymanV2Pool(
                client=tinyman_v2_client,
                asset_a=swap["pool"]["asset_1_id"],
                asset_b=swap["pool"]["asset_2_id"],
                fetch=True,
            )
        else:
            raise NotImplementedError()
        pools.append(pool)

    route = Route(
        asset_in=tinyman_v2_client.fetch_asset(asset_in_id),
        asset_out=tinyman_v2_client.fetch_asset(asset_out_id),
        pools=pools,
    )
    return route


def fetch_best_route(
    tinyman_v1_client: TinymanClient,
    tinyman_v2_client: TinymanV2Client,
    asset_in_id: int,
    asset_out_id: int,
    swap_type: str,
    amount: int,
):
    asset_in = tinyman_v2_client.fetch_asset(asset_in_id)
    asset_out = tinyman_v2_client.fetch_asset(asset_out_id)
    routes = []

    v1_pool = TinymanV1Pool(
        client=tinyman_v1_client,
        asset_a=asset_in,
        asset_b=asset_out,
        fetch=True,
    )
    if v1_pool.exists:
        direct_v1_route = Route(asset_in=asset_in, asset_out=asset_out, pools=[v1_pool])
        routes.append(direct_v1_route)

    v2_pool = TinymanV2Pool(
        client=tinyman_v2_client,
        asset_a=asset_in,
        asset_b=asset_out,
        fetch=True,
    )
    if v2_pool.exists:
        direct_v2_route = Route(asset_in=asset_in, asset_out=asset_out, pools=[v2_pool])
        routes.append(direct_v2_route)

    try:
        smart_swap_route = fetch_smart_swap_route(
            tinyman_v1_client=tinyman_v1_client,
            tinyman_v2_client=tinyman_v2_client,
            asset_in_id=asset_in_id,
            asset_out_id=asset_out_id,
            swap_type=swap_type,
            amount=amount,
        )
    except Exception:  # TODO: Handle the exception properly.
        smart_swap_route = None

    if smart_swap_route is not None:
        routes.append(smart_swap_route)

    if swap_type == FIXED_INPUT_SWAP_TYPE:
        best_route = get_best_fixed_input_route(routes=routes, amount_in=amount)
    elif swap_type == FIXED_OUTPUT_SWAP_TYPE:
        best_route = get_best_fixed_output_route(routes=routes, amount_out=amount)
    else:
        raise NotImplementedError()

    return best_route

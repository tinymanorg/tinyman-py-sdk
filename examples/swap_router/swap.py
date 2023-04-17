# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
from typing import Optional
from urllib.parse import quote_plus

from examples.v2.utils import get_algod
from tinyman.assets import Asset
from tinyman.assets import AssetAmount
from tinyman.optin import prepare_asset_optin_transactions
from tinyman.swap_router.routes import Route
from tinyman.swap_router.routes import get_best_fixed_input_route
from tinyman.swap_router.swap_router import fetch_best_route_suggestion
from tinyman.swap_router.swap_router import (
    get_swap_router_app_opt_in_required_asset_ids,
    prepare_swap_router_asset_opt_in_transaction,
)
from tinyman.v1.client import TinymanClient
from tinyman.v1.pools import Pool as TinymanV1Pool
from tinyman.v2.client import TinymanV2Client
from tinyman.v2.client import TinymanV2TestnetClient
from tinyman.v2.pools import Pool as TinymanV2Pool


def fetch_routes(
    tinyman_v1_client: Optional[TinymanClient],
    tinyman_v2_client: TinymanV2Client,
    asset_in: Asset,
    asset_out: Asset,
    swap_type: str,
    amount: int,
) -> "list[Route]":
    """
    This is an example route list preparation.
    You can build yor own route list according to your needs.

    The list contains;
    V1 Direct Route if it exists and has liquidity,
    V2 Direct Route if it exists and has liquidity,
    V2 Indirect (2 swap) Route provided by Tinyman API.
    """
    routes = []

    if tinyman_v1_client is not None:
        # Don't check V1 pool if the client is not provided
        v1_pool = TinymanV1Pool(
            client=tinyman_v1_client,
            asset_a=asset_in,
            asset_b=asset_out,
            fetch=True,
        )
        if v1_pool.exists and v1_pool.issued_liquidity:
            v1_direct_route = Route(
                asset_in=asset_in, asset_out=asset_out, pools=[v1_pool]
            )
            routes.append(v1_direct_route)

    v2_pool = TinymanV2Pool(
        client=tinyman_v2_client,
        asset_a=asset_in,
        asset_b=asset_out,
        fetch=True,
    )
    if v2_pool.exists and v2_pool.issued_pool_tokens:
        v2_direct_route = Route(asset_in=asset_in, asset_out=asset_out, pools=[v2_pool])
        routes.append(v2_direct_route)

    route = fetch_best_route_suggestion(
        tinyman_client=tinyman_v2_client,
        asset_in=asset_in,
        asset_out=asset_out,
        swap_type=swap_type,
        amount=amount,
    )
    if len(route.pools) > 1:
        routes.append(route)

    return routes


def swap(asset_in_id, asset_out_id, amount, account):
    algod = get_algod()

    # tinyman_v1_client = TinymanTestnetClient(algod_client=algod, user_address=account["address"])
    tinyman_v2_client = TinymanV2TestnetClient(
        algod_client=algod, user_address=account["address"]
    )

    asset_in = tinyman_v2_client.fetch_asset(asset_in_id)
    asset_out = tinyman_v2_client.fetch_asset(asset_out_id)

    asset_amount_in = AssetAmount(asset_in, amount)
    routes = fetch_routes(
        tinyman_v1_client=None,
        tinyman_v2_client=tinyman_v2_client,
        asset_in=asset_in,
        asset_out=asset_out,
        swap_type="fixed-input",
        amount=asset_amount_in.amount,
    )

    if routes:
        print("Routes:")
        for index, route in enumerate(routes, start=1):
            print(index, route)
    else:
        print("There is no route available.")
        return

    print("Best Route:")
    best_route = get_best_fixed_input_route(
        routes=routes, amount_in=asset_amount_in.amount
    )
    print(best_route)

    if best_route:
        print("Quotes:")
        quotes = best_route.get_fixed_input_quotes(amount_in=asset_amount_in.amount)
        for index, quote in enumerate(quotes, start=1):
            print(index, quote)
    else:
        print("Couldn't calculate the quotes.")
        return

    suggested_params = tinyman_v2_client.algod.suggested_params()

    if len(quotes) > 1:
        # Swap Router Flow
        print("The best route is single hop swap. Prepare swap router transactions.")

        # 1 - Transfer input to swap router app account
        # 2 - Swap router app call
        txn_group = best_route.prepare_swap_router_transactions_from_quotes(
            quotes=quotes, suggested_params=suggested_params
        )

        # Swap router app account may require to opt in to some assets.
        opt_in_required_asset_ids = get_swap_router_app_opt_in_required_asset_ids(
            algod_client=tinyman_v2_client.algod,
            router_app_id=tinyman_v2_client.router_app_id,
            asset_ids=best_route.asset_ids,
        )
        if opt_in_required_asset_ids:
            opt_in_txn_group = prepare_swap_router_asset_opt_in_transaction(
                router_app_id=tinyman_v2_client.router_app_id,
                asset_ids=opt_in_required_asset_ids,
                user_address=account["address"],
                suggested_params=suggested_params,
            )
            txn_group = opt_in_txn_group + txn_group

    else:
        # Direct Swap Flow
        pool = best_route.pools[0]
        quote = quotes[0]

        if pool.client.version == "v1":
            print(f"The best route is direct swap using {pool}.")
            print("V1 swap flow is not handled in this example.")
            return

        elif pool.client.version == "v2":
            print(f"The best route is direct swap using {pool}.")
            txn_group = pool.prepare_swap_transactions_from_quote(
                quote=quote,
                user_address=account["address"],
                suggested_params=suggested_params,
            )
        else:
            raise NotImplementedError()

    # User account may require to opt in to output asset.
    if not tinyman_v2_client.asset_is_opted_in(
        asset_id=asset_out_id, user_address=account["address"]
    ):
        user_opt_in_txn_group = prepare_asset_optin_transactions(
            asset_id=asset_out_id,
            sender=account["address"],
            suggested_params=suggested_params,
        )
        txn_group = user_opt_in_txn_group + txn_group

    # Sign
    txn_group.sign_with_private_key(account["address"], account["private_key"])

    # Submit transactions to the network and wait for confirmation
    txn_info = tinyman_v2_client.submit(txn_group, wait=True)
    print("Transaction Info")
    print(txn_info)

    print(
        f"\nCheck the transaction group on Algoexplorer: https://testnet.algoexplorer.io/tx/group/{quote_plus(txn_group.id)}"
    )


if __name__ == "__main__":
    # TODO: Set Account
    account = {
        "address": "ALGORAND_ADDRESS_HERE",
        "private_key": "base64_private_key_here",
    }

    # TODO: Set asset ids
    asset_in_id, asset_out_id = 0, 21582668

    swap(asset_in_id, asset_out_id, 1_000_000, account)

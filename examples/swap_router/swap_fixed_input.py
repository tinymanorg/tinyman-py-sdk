from algosdk.account import generate_account
from algosdk.v2client.algod import AlgodClient

from tinyman.swap_router.swap_router import fetch_swap_route_quotes, prepare_swap_router_transactions_from_quotes
from tinyman.v1.client import TinymanTestnetClient
from tinyman.v2.client import TinymanV2TestnetClient

ALGO_ASSET_ID = 0
USDC_ASSET_ID = 10458941
private_key, address = generate_account()

algod_client = AlgodClient("", "https://testnet-api.algonode.network")

tinyman_v1_client = TinymanTestnetClient(algod_client=algod_client)
tinyman_v2_client = TinymanV2TestnetClient(algod_client=algod_client)

swap_type = "fixed-input"
amount = 1_000_000

route_pools_and_quotes = fetch_swap_route_quotes(
    tinyman_v1_client=tinyman_v1_client,
    tinyman_v2_client=tinyman_v2_client,
    asset_in_id=ALGO_ASSET_ID,
    asset_out_id=USDC_ASSET_ID,
    swap_type=swap_type,
    amount=amount
)
print(route_pools_and_quotes)

txn_group = prepare_swap_router_transactions_from_quotes(
    route_pools_and_quotes=route_pools_and_quotes,
    swap_type=swap_type,
    user_address=address,
    suggested_params=algod_client.suggested_params()
)

for txn in txn_group.transactions:
    print()
    print(txn.dictify())

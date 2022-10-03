# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
from pprint import pprint
from urllib.parse import quote_plus

from tinyman.assets import AssetAmount

from examples.v2.tutorial.common import get_account, get_assets
from examples.v2.utils import get_algod
from tinyman.v2.client import TinymanV2TestnetClient


account = get_account()
algod = get_algod()
client = TinymanV2TestnetClient(algod_client=algod, user_address=account["address"])

ASSET_A_ID, ASSET_B_ID = get_assets()["ids"]
ASSET_A = client.fetch_asset(ASSET_A_ID)
ASSET_B = client.fetch_asset(ASSET_B_ID)
pool = client.fetch_pool(ASSET_A_ID, ASSET_B_ID)

# Add flexible liquidity (advanced)
# txn_group = pool.prepare_add_liquidity_transactions(
#     amounts_in={
#         pool.asset_1: AssetAmount(pool.asset_1, 5_000_000),
#         pool.asset_2: AssetAmount(pool.asset_2, 7_000_000)
#     },
#     min_pool_token_asset_amount="Do your own calculation"
# )

quote = pool.fetch_single_asset_add_liquidity_quote(
    amount_a=AssetAmount(pool.asset_1, 10_000_000),
)

print("\nAdd Liquidity Quote:")
print(quote)

txn_group = pool.prepare_add_liquidity_transactions_from_quote(quote=quote)

if not client.asset_is_opted_in(asset_id=pool.pool_token_asset.id):
    # Opt-in to the pool token
    opt_in_txn_group = pool.prepare_pool_token_asset_optin_transactions()
    # You can merge the transaction groups
    txn_group = txn_group + opt_in_txn_group

# Sign
txn_group.sign_with_private_key(account["address"], account["private_key"])

# Submit transactions to the network and wait for confirmation
txn_info = txn_group.submit(algod, wait=True)
print("Transaction Info")
pprint(txn_info)

print(
    f"Check the transaction group on Algoexplorer: https://testnet.algoexplorer.io/tx/group/{quote_plus(txn_group.id)}"
)

pool.refresh()
pool_position = pool.fetch_pool_position()
share = pool_position["share"] * 100
print(f"Pool Tokens: {pool_position[pool.pool_token_asset]}")
print(f"Assets: {pool_position[ASSET_A]}, {pool_position[ASSET_B]}")
print(f"Share of pool: {share:.3f}%")

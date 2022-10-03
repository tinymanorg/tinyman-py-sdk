# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
from pprint import pprint
from urllib.parse import quote_plus

from tinyman.assets import AssetAmount

from examples.v2.tutorial.common import get_account, get_algod, get_assets
from tinyman.v2.client import TinymanV2TestnetClient


account = get_account()
algod = get_algod()
client = TinymanV2TestnetClient(algod_client=algod, user_address=account["address"])

ASSET_A_ID, ASSET_B_ID = get_assets()["ids"]
ASSET_A = client.fetch_asset(ASSET_A_ID)
ASSET_B = client.fetch_asset(ASSET_B_ID)
pool = client.fetch_pool(ASSET_A_ID, ASSET_B_ID)

# Opt-in to the pool token
txn_group_1 = pool.prepare_pool_token_asset_optin_transactions()

# Get initial add liquidity quote
quote = pool.fetch_initial_add_liquidity_quote(
    amount_a=AssetAmount(pool.asset_1, 10_000_000),
    amount_b=AssetAmount(pool.asset_2, 10_000_000),
)
print("Quote:")
print(quote)

txn_group_2 = pool.prepare_add_liquidity_transactions_from_quote(quote)

# You can merge the transaction groups
txn_group = txn_group_1 + txn_group_2

# Sign
txn_group.sign_with_private_key(account["address"], account["private_key"])

# Submit transactions to the network and wait for confirmation
txinfo = txn_group.submit(algod, wait=True)
print("Transaction Info")
pprint(txinfo)

print(
    f"Check the transaction group on Algoexplorer: https://testnet.algoexplorer.io/tx/group/{quote_plus(txn_group.id)}"
)

pool.refresh()
pool_position = pool.fetch_pool_position()
share = pool_position["share"] * 100
print(f"Pool Tokens: {pool_position[pool.pool_token_asset]}")
print(f"Assets: {pool_position[ASSET_A]}, {pool_position[ASSET_B]}")
print(f"Share of pool: {share:.3f}%")

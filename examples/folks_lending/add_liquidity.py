from algosdk.v2client.algod import AlgodClient

from tinyman.folks_lending.constants import (
    TESTNET_FOLKS_POOL_MANAGER_APP_ID,
    TESTNET_FOLKS_WRAPPER_LENDING_POOL_APP_ID)
from tinyman.folks_lending.transactions import \
    prepare_add_liquidity_transaction_group
from tinyman.folks_lending.utils import get_lending_pools
from tinyman.v2.client import TinymanV2TestnetClient
from tinyman.v2.constants import TESTNET_VALIDATOR_APP_ID_V2

algod = AlgodClient("", "https://testnet-api.algonode.network")
account_sk, account_address = ('YOUR PRIVATE KEY HERE', 'YOUR ADDRESS HERE')
client = TinymanV2TestnetClient(algod_client=algod, user_address=account_address)

asset_1_id = 67395862  # USDC
asset_2_id = 0  # Algo

# Get f_asset ids

folks_pools = get_lending_pools(algod, TESTNET_FOLKS_POOL_MANAGER_APP_ID)
temp = dict()
for folks_pool in folks_pools:
    temp[folks_pool['asset_id']] = folks_pool
folks_pools = temp

f_asset_1_id = folks_pools[asset_1_id]['f_asset_id']
f_asset_2_id = folks_pools[asset_2_id]['f_asset_id']

pool = client.fetch_pool(f_asset_1_id, f_asset_2_id, fetch=True)

# Add liquidity

txn_group = prepare_add_liquidity_transaction_group(
    sender=account_address,
    suggested_params=algod.suggested_params(),
    wrapper_app_id=TESTNET_FOLKS_WRAPPER_LENDING_POOL_APP_ID,
    tinyman_amm_app_id=TESTNET_VALIDATOR_APP_ID_V2,
    lending_app_1_id=folks_pools[asset_1_id]['pool_app_id'],
    lending_app_2_id=folks_pools[asset_2_id]['pool_app_id'],
    lending_manager_app_id=TESTNET_FOLKS_POOL_MANAGER_APP_ID,
    tinyman_pool_address=pool.address,
    asset_1_id=asset_1_id,
    asset_2_id=asset_2_id,
    f_asset_1_id=f_asset_1_id,
    f_asset_2_id=f_asset_2_id,
    liquidity_token_id=pool.pool_token_asset.id,
    asset_1_amount=10000,
    asset_2_amount=10000
)

txn_group.sign_with_private_key(account_address, account_sk)
txn_group.submit(algod, True)

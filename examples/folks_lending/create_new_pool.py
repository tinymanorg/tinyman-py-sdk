from algosdk import transaction
from algosdk.v2client.algod import AlgodClient

from tinyman.folks_lending.constants import (
    TESTNET_FOLKS_POOL_MANAGER_APP_ID,
    TESTNET_FOLKS_WRAPPER_LENDING_POOL_APP_ID)
from tinyman.folks_lending.transactions import \
    prepare_asset_optin_transaction_group
from tinyman.folks_lending.utils import get_lending_pools
from tinyman.utils import TransactionGroup
from tinyman.v2.client import TinymanV2TestnetClient

algod = AlgodClient("", "https://testnet-api.algonode.network")
account_sk, account_address = ('YOUR PRIVATE KEY HERE', 'YOUR ADDRESS HERE')
client = TinymanV2TestnetClient(algod_client=algod, user_address=account_address)

asset_1_id = 67396528  # goBTC
asset_2_id = 0  # Algo

# Get f_asset ids

folks_pools = get_lending_pools(algod, TESTNET_FOLKS_POOL_MANAGER_APP_ID)
temp = dict()
for folks_pool in folks_pools:
    temp[folks_pool['asset_id']] = folks_pool
folks_pools = temp

f_asset_1_id = folks_pools[asset_1_id]['f_asset_id']
f_asset_2_id = folks_pools[asset_2_id]['f_asset_id']

pool = client.fetch_pool(f_asset_1_id, f_asset_2_id)

# Opt-in to assets

txns = [
    transaction.AssetOptInTxn(
        sender=account_address,
        sp=algod.suggested_params(),
        index=asset_1_id
    ),
    transaction.AssetOptInTxn(
        sender=account_address,
        sp=algod.suggested_params(),
        index=f_asset_1_id
    ),
    transaction.AssetOptInTxn(
        sender=account_address,
        sp=algod.suggested_params(),
        index=f_asset_2_id
    )
]

if asset_2_id != 0:
    txns.append(
        transaction.AssetOptInTxn(
            sender=account_address,
            sp=algod.suggested_params(),
            index=asset_2_id
        )
    )
txn_group = TransactionGroup(txns)
txn_group.sign_with_private_key(account_address, account_sk)
txn_group.submit(algod, True)

# Bootstrap pool.

txn_group = pool.prepare_bootstrap_transactions(
    user_address=account_address,
    suggested_params=algod.suggested_params(),
)
txn_group.sign_with_private_key(account_address, account_sk)
txn_group.submit(algod, True)

# Opt-in to pool token.

pool = client.fetch_pool(f_asset_1_id, f_asset_2_id, fetch=True)

txn_group = TransactionGroup([
    transaction.AssetOptInTxn(
        sender=account_address,
        sp=algod.suggested_params(),
        index=pool.pool_token_asset.id
    )
])
txn_group.sign_with_private_key(account_address, account_sk)
txn_group.submit(algod, True)

# Send an asset_optin appcall.

txn_group = prepare_asset_optin_transaction_group(
    sender=account_address,
    suggested_params=algod.suggested_params(),
    wrapper_app_id=TESTNET_FOLKS_WRAPPER_LENDING_POOL_APP_ID,
    assets_to_optin=[asset_1_id, asset_2_id, f_asset_1_id, f_asset_2_id, pool.pool_token_asset.id]
)
txn_group.sign_with_private_key(account_address, account_sk)
txn_group.submit(algod, True)

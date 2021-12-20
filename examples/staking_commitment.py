# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.

from tinyman.v1.client import TinymanTestnetClient

from tinyman.v1.staking import prepare_commit_transaction

# Hardcoding account keys is not a great practice. This is for demonstration purposes only.
# See the README & Docs for alternative signing methods.
account = {
    'address': 'ALGORAND_ADDRESS_HERE',
    'private_key': 'base64_private_key_here', # Use algosdk.mnemonic.to_private_key(mnemonic) if necessary
}

client = TinymanTestnetClient(user_address=account['address'])
# By default all subsequent operations are on behalf of user_address

# Fetch our two assets of interest
TINYUSDC = client.fetch_asset(21582668)
ALGO = client.fetch_asset(0)

# Fetch the pool we will work with
pool = client.fetch_pool(TINYUSDC, ALGO)


sp = client.algod.suggested_params()

txn_group = prepare_commit_transaction(
    app_id=client.staking_app_id,
    program_id=1,
    program_account='B4XVZ226UPFEIQBPIY6H454YA4B7HYXGEM7UDQR2RJP66HVLOARZTUTS6Q',
    pool_asset_id=pool.liquidity_asset.id,
    amount=700_000_000,
    sender=account['address'],
    suggested_params=sp,
)

txn_group.sign_with_private_key(account['address'], account['private_key'])
result = client.submit(txn_group, wait=True)
print(result)



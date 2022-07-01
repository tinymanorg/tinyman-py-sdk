# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.


# This example has exactly the same functionality as swapping1.py but is purposely more verbose, using less convenience functions.
# It is intended to give an understanding of what happens under those convenience functions.

from tinyman.v1.pools import Pool
from tinyman.assets import Asset
from algosdk.future.transaction import wait_for_confirmation
from algosdk.v2client.algod import AlgodClient
from tinyman.v1.client import TinymanClient


# Hardcoding account keys is not a great practice. This is for demonstration purposes only.
# See the README & Docs for alternative signing methods.
account = {
    'address': 'ALGORAND_ADDRESS_HERE',
    'private_key': 'base64_private_key_here', # Use algosdk.mnemonic.to_private_key(mnemonic) if necessary
}


algod = AlgodClient('<TOKEN>', 'http://localhost:8080', headers={'User-Agent': 'algosdk'})

client = TinymanClient(
    algod_client=algod,
    validator_app_id=21580889,
)


# Check if the account is opted into Tinyman and optin if necessary
if(not client.is_opted_in(account['address'])):
    print('Account not opted into app, opting in now..')
    transaction_group = client.prepare_app_optin_transactions(account['address'])
    for i, txn in enumerate(transaction_group.transactions):
        if txn.sender == account['address']:
            transaction_group.signed_transactions[i] = txn.sign(account['private_key'])
    txid = client.algod.send_transactions(transaction_group.signed_transactions)
    wait_for_confirmation(algod, txid)


# Fetch our two assets of interest
TINYUSDC = Asset(id=21582668, name='TinyUSDC', unit_name='TINYUSDC', decimals=6)
ALGO = Asset(id=0, name='Algo', unit_name='ALGO', decimals=6)

# Create the pool we will work with and fetch its on-chain state
pool = Pool(client, asset_a=TINYUSDC, asset_b=ALGO, fetch=True)


# Get a quote for a swap of 1 ALGO to TINYUSDC with 1% slippage tolerance
quote = pool.fetch_fixed_input_swap_quote(ALGO(1_000_000), slippage=0.01)
print(quote)
print(f'TINYUSDC per ALGO: {quote.price}')
print(f'TINYUSDC per ALGO (worst case): {quote.price_with_slippage}')

# We only want to sell if ALGO is > 180 TINYUSDC (It's testnet!)
if quote.price_with_slippage > 180:
    print(f'Swapping {quote.amount_in} to {quote.amount_out_with_slippage}')
    # Prepare a transaction group
    transaction_group = pool.prepare_swap_transactions(
        amount_in=quote.amount_in,
        amount_out=quote.amount_out_with_slippage,
        swap_type='fixed-input',
        swapper_address=account['address'],
    )
    # Sign the group with our key
    for i, txn in enumerate(transaction_group.transactions):
        if txn.sender == account['address']:
            transaction_group.signed_transactions[i] = txn.sign(account['private_key'])
    txid = algod.send_transactions(transaction_group.signed_transactions)
    wait_for_confirmation(algod, txid)

    # Check if any excess remaining after the swap
    excess = pool.fetch_excess_amounts(account['address'])
    if TINYUSDC.id in excess:
        amount = excess[TINYUSDC.id]
        print(f'Excess: {amount}')
        # We might just let the excess accumulate rather than redeeming if its < 1 TinyUSDC
        if amount > 1_000_000:
            transaction_group = pool.prepare_redeem_transactions(amount, account['address'])
            # Sign the group with our key
            for i, txn in enumerate(transaction_group.transactions):
                if txn.sender == account['address']:
                    transaction_group.signed_transactions[i] = txn.sign(account['private_key'])
            txid = algod.send_transactions(transaction_group.signed_transactions)
            wait_for_confirmation(algod, txid)

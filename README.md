# tinyman-py-sdk
Tinyman Python SDK


## Design Goal
This SDK is designed for automated interaction with the Tinyman AMM. It will be most useful for developers who wish to create automated trading programs/bots. It may also be useful to create an alternative UI but that is not a design goal of this library.
It is designed to be reasonably low level so that pieces can be used in isolation. 

## Status
This SDK is currently under active early development and should not be considered stable.

## Installation
tinyman-py-sdk is not yet released on PYPI. It can be installed directly from this repository with pip:

`pip install git+https://github.com/tinymanorg/tinyman-py-sdk.git`


## Sneak Preview

```python
from tinyman.v1.client import TinymanTestnetClient

client = TinymanTestnetClient()

# Fetch our two assets of interest
TINYUSDC = client.fetch_asset(21582668)
ALGO = client.fetch_asset(0)

# Fetch the pool we will work with
pool = client.fetch_pool(TINYUSDC, ALGO)

# Get a quote for a swap of 1 ALGO to TINYUSDC with 1% slippage tolerance
quote = pool.fetch_fixed_input_swap_quote(ALGO(1_000_000), slippage=0.01)
print(quote)
print(f'TINYUSDC per ALGO: {quote.price}')
print(f'TINYUSDC per ALGO (worst case): {quote.price_with_slippage}')

# See the examples for the rest...

```

## Examples

### Basic Swapping
[swapping1.py](examples/swapping1.py)
This example demonstrates basic functionality including:
* retrieving Pool details
* getting a swap quote
* preparing swap transactions
* signing transactions
* submitting transactions
* checking excess amounts
* preparing redeem transactions

[swapping1_less_convenience.py](examples/swapping1_less_convenience.py)
This example has exactly the same functionality as [swapping1.py](examples/swapping1.py) but is purposely more verbose, using less convenience functions.


### Basic Pooling
[pooling1.py](examples/pooling1.py)
This example demonstrates retrieving the current pool position/share for an address.

### Basic Add Liquidity (Minting)
[add_liquidity1.py](examples/add_liquidity1.py)
This example demonstrates add liquidity to an existing pool.

### Basic Burning
TODO


## Conventions

* Methods starting with `fetch_` all make network requests to fetch current balances/state.
* Methods of the form `prepare_X_transactions` all return `TransactionGroup` objects (see below).
* All asset amounts are returned as `AssetAmount` objects which contain an `Asset` and `amount` (`int`).
* All asset amount inputs are expected as micro units e.g. 1 Algo = 1_000_000 micro units.

## Signing & Submission

The SDk separates transaction preparation from signing and submission to leave the developer in full control of how transactions are signed and submitted to the network.

### Preparation
The `prepare_X_transactions` methods all return a `TransactionGroup` object. This is a container object containing a list of transaction objects (`.transactions`) and a list for signed transactions (`.signed_transactions`). 

```python
transaction_group = client.prepare_app_optin_transactions(account['address'])
```


### Signing
In most cases some of the transactions have a corresponding entry in `.signed_transactions` because they have been signed by the Pool LogicSig. The remaining transactions should be signed by the 'user'.


The `TransactionGroup` includes a method to do this when signing with a private key:

```python
transaction_group.sign_with_private_key(account['address'], account['private_key'])
```

This helper method is equivalent to the following:
```python
for i, txn in enumerate(transaction_group.transactions):
    if txn.sender == account['address']:
        transaction_group.signed_transactions[i] = txn.sign(account['private_key'])
```

Any alternative method of signing can be used here following the same pattern. For example using KMD:
```python
kmd = algosdk.kmd.KMDClient(KMD_TOKEN, KMD_ADDRESS)
handle = kmd.init_wallet_handle(KMD_WALLET_ID, KMD_WALLET_PASSWORD)
for i, txn in enumerate(transaction_group.transactions):
    if txn.sender == account['address']:
        transaction_group.signed_transactions[i] = kmd.sign_transaction(handle, KMD_WALLET_PASSWORD, txn)
```

A User account LogicSig can also be used in a similar way or using the `sign_with_logicisg` convenience method:
```python
transaction_group.sign_with_logicisg(logicsig)
```

### Submission

A `TransactionGroup` containing fully signed transactions can be submitted to the network in either of two ways:

Using an Algod client:

```python
algod = AlgodClient(TOKEN, ADDRESS, headers={'User-Agent': 'algosdk'})
txid = algod.send_transactions(transaction_group.signed_transactions)
```

Or, using the convenience method of the `TinymanClient`:

```python
result = client.submit(transaction_group, wait=True)
```

This method submits the signed transactions and optionally waits for confirmation.


# License

tinyman-py-sdk is licensed under a MIT license except for the exceptions listed below. See the LICENSE file for details.

## Exceptions
`tinyman/v1/asc.json` is currently unlicensed. It may be used by this SDK but may not be used in any other way or be distributed separately without the express permission of Tinyman.

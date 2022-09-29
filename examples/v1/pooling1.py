# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.

from tinyman.v1.client import TinymanTestnetClient
from algosdk.v2client.algod import AlgodClient


# Hardcoding account keys is not a great practice. This is for demonstration purposes only.
# See the README & Docs for alternative signing methods.
account = {
    "address": "ALGORAND_ADDRESS_HERE",
    "private_key": "base64_private_key_here",  # Use algosdk.mnemonic.to_private_key(mnemonic) if necessary
}

algod = AlgodClient(
    "<TOKEN>", "http://localhost:8080", headers={"User-Agent": "algosdk"}
)
client = TinymanTestnetClient(algod_client=algod, user_address=account["address"])
# By default all subsequent operations are on behalf of user_address

# Fetch our two assets of interest
TINYUSDC = client.fetch_asset(21582668)
ALGO = client.fetch_asset(0)

# Fetch the pool we will work with
pool = client.fetch_pool(TINYUSDC, ALGO)

info = pool.fetch_pool_position()
share = info["share"] * 100
print(f"Pool Tokens: {info[pool.liquidity_asset]}")
print(f"Assets: {info[TINYUSDC]}, {info[ALGO]}")
print(f"Share of pool: {share:.3f}%")

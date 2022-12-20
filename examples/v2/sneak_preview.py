# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
from examples.v2.utils import get_algod
from tinyman.v2.client import TinymanV2TestnetClient

algod = get_algod()
client = TinymanV2TestnetClient(algod_client=algod)

# Fetch our two assets of interest
USDC = client.fetch_asset(10458941)
ALGO = client.fetch_asset(0)

# Fetch the pool we will work with
pool = client.fetch_pool(USDC, ALGO)
print(f"Pool Info: {pool.info()}")

# Get a quote for a swap of 1 ALGO to USDC with 1% slippage tolerance
quote = pool.fetch_fixed_input_swap_quote(amount_in=ALGO(1_000_000), slippage=0.01)
print(quote)
print(f"USDC per ALGO: {quote.price}")
print(f"USDC per ALGO (worst case): {quote.price_with_slippage}")

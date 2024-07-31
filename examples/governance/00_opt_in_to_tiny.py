from examples.v2.utils import get_algod
from tinyman.governance.client import TinymanGovernanceTestnetClient

from tinyman.governance.constants import TESTNET_TINY_ASSET_ID

# Hardcoding account keys is not a great practice. This is for demonstration purposes only.
# See the README & Docs for alternative signing methods.
account = {
    "address": "ALGORAND_ADDRESS_HERE",
    "private_key": "base64_private_key_here",
}

algod = get_algod()

# Client
governance_client = TinymanGovernanceTestnetClient(
    algod_client=algod,
    user_address=account["address"]
)

if not governance_client.asset_is_opted_in(TESTNET_TINY_ASSET_ID):
    txn_group = governance_client.prepare_asset_optin_transactions(TESTNET_TINY_ASSET_ID)
    txn_group.sign_with_private_key(address=account["address"], private_key=account["private_key"])
    result = txn_group.submit(algod, wait=True)
    print("TXN:", result)

print("Get some TINY token.")

from examples.v2.utils import get_algod
from tinyman.governance.client import TinymanGovernanceTestnetClient

from tinyman.governance.constants import TESTNET_TINY_ASSET_ID
from tinyman.governance.rewards.utils import group_adjacent_period_indexes

# Hardcoding account keys is not a great practice. This is for demonstration purposes only.
# See the README & Docs for alternative signing methods.
account = {
    "address": "ALGORAND_ADDRESS_HERE",
    "private_key": "base64_private_key_here",
}

algod = get_algod()


def get_tiny_balance(address):
    account_info = algod.account_info(account["address"])
    assets = {a["asset-id"]: a for a in account_info["assets"]}
    return assets.get(TESTNET_TINY_ASSET_ID, {}).get("amount", 0)


# Client
governance_client = TinymanGovernanceTestnetClient(
    algod_client=algod,
    user_address=account["address"]
)

print("TINY balance before TXN:", get_tiny_balance(account["address"]))

pending_reward_period_indexes = governance_client.get_pending_reward_period_indexes()
print(pending_reward_period_indexes)
index_groups = group_adjacent_period_indexes(pending_reward_period_indexes)

for index_group in index_groups:
    print("Index Group:", index_group)
    txn_group = governance_client.prepare_claim_reward_transactions(
        period_index_start=index_group[0],
        period_count=len(index_group),
    )
    txn_group.sign_with_private_key(account["address"], account["private_key"])
    txn_group.submit(algod, wait=True)

    account_state = governance_client.fetch_account_state()
    print("TINY balance after TXN:", get_tiny_balance(account["address"]))

import time

from examples.v2.utils import get_algod
from tinyman.governance.client import TinymanGovernanceTestnetClient
from tinyman.governance.constants import WEEK
from tinyman.governance.vault.constants import MIN_LOCK_TIME

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

account_state = governance_client.fetch_account_state()
print("Account State before TXN:", account_state)

end_timestamp_of_current_week = (int(time.time()) // WEEK + 1) * WEEK
lock_end_timestamp = end_timestamp_of_current_week + MIN_LOCK_TIME

# lock_end_timestamp = int(time.time()) + 100

txn_group = governance_client.prepare_create_lock_transactions(
    locked_amount=10_000_000,
    lock_end_time=lock_end_timestamp,
)
txn_group.sign_with_private_key(account["address"], account["private_key"])
txn_group.submit(algod, wait=True)

account_state = governance_client.fetch_account_state()
print("Account State after TXN:", account_state)

tiny_power = governance_client.get_tiny_power()
print("TINY POWER:", tiny_power)

total_tiny_power = governance_client.get_total_tiny_power()
print("Total TINY POWER:", total_tiny_power)
print(f"User TINY Power %{(tiny_power / total_tiny_power) * 100}")

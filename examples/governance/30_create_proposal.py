from examples.v2.utils import get_algod
from tinyman.governance.client import TinymanGovernanceTestnetClient
from tinyman.governance.proposal_voting.transactions import generate_proposal_metadata
from tinyman.governance.utils import generate_cid_from_proposal_metadata

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
    user_address=account["address"],
)

account_state = governance_client.fetch_account_state()
print("Account State before TXN:", account_state)

tiny_power = governance_client.get_tiny_power()
print("TINY POWER:", tiny_power)
total_tiny_power = governance_client.get_total_tiny_power()
print("Total TINY POWER:", total_tiny_power)
print(f"User TINY Power %{(tiny_power / total_tiny_power) * 100}")

# Generate metadata and proposal ID
metadata = generate_proposal_metadata(
    title="Proposal #3",
    description="Description #3",
    category="governance",
    discussion_url="http://www.discussion-url.com",
    poll_url="http://www.poll-url.com",
)
print(metadata)
proposal_id = generate_cid_from_proposal_metadata(metadata)

# Upload metadata
governance_client.upload_proposal_metadata(proposal_id, metadata)

# Submit transactions
txn_group = governance_client.prepare_create_proposal_transactions(proposal_id=proposal_id)
txn_group.sign_with_private_key(address=account["address"], private_key=account["private_key"])
result = txn_group.submit(algod=algod, wait=True)
print(result)

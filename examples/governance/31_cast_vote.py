from examples.v2.utils import get_algod
from tinyman.governance.client import TinymanGovernanceTestnetClient

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

proposal_id = "bafkreicgbzr64gmjl642tazzzuomrbzn2uimhhig2wq2ch7tjcyee5cxh4"

# Upload metadata
txn_group = governance_client.prepare_cast_vote_transactions(proposal_id=proposal_id, vote=0)
txn_group.sign_with_private_key(address=account["address"], private_key=account["private_key"])
result = txn_group.submit(algod=algod, wait=True)
print(result)

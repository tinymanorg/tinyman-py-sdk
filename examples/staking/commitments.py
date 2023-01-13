import requests
from tinyman.staking import parse_commit_transaction
from tinyman.staking.constants import TESTNET_STAKING_APP_ID

app_id = TESTNET_STAKING_APP_ID
result = requests.get(
    f"https://indexer.testnet.algoexplorerapi.io/v2/transactions?application-id={app_id}&latest=50"
).json()
for txn in result["transactions"]:
    commit = parse_commit_transaction(txn, app_id)
    if commit:
        print(commit)
        print()

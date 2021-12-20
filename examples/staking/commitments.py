import requests
from tinyman.v1.staking import parse_commit_transaction

app_id = 51948952
result = requests.get(f'https://indexer.testnet.algoexplorerapi.io/v2/transactions?application-id={app_id}&latest=50').json()
for txn in result['transactions']:
    commit = parse_commit_transaction(txn, app_id)
    if commit:
        print(commit)
        print()
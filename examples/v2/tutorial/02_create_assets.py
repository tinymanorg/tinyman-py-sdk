# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
import json
import os

from examples.v2.tutorial.common import (
    get_account,
    get_assets_file_path,
    create_asset,
)
from examples.v2.utils import get_algod
from tinyman.v2.client import TinymanV2TestnetClient


assets_file_path = get_assets_file_path()

try:
    size = os.path.getsize(assets_file_path)
except FileNotFoundError:
    size = 0
else:
    if size > 0:
        raise Exception(f"The file({assets_file_path}) is not empty")

account = get_account()
algod = get_algod()
client = TinymanV2TestnetClient(algod_client=algod, user_address=account["address"])

account_info = algod.account_info(account["address"])
if not account_info["amount"]:
    print(
        f"Go to https://bank.testnet.algorand.network/?account={account['address']} and fund your account."
    )
    exit(1)

ASSET_A_ID = create_asset(algod, account["address"], account["private_key"])
ASSET_B_ID = create_asset(algod, account["address"], account["private_key"])

assets_data = {"ids": [ASSET_A_ID, ASSET_B_ID]}

with open(assets_file_path, "w", encoding="utf-8") as f:
    json.dump(assets_data, f, ensure_ascii=False, indent=4)

print(f"Generated Assets: {[ASSET_A_ID, ASSET_B_ID]}")
print("View on Algoexplorer:")
print(f"https://testnet.algoexplorer.io/asset/{ASSET_A_ID}")
print(f"https://testnet.algoexplorer.io/asset/{ASSET_B_ID}")

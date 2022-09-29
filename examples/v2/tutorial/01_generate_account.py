import json
import os

from algosdk.account import generate_account
from algosdk.mnemonic import from_private_key

from examples.v2.tutorial.common import get_account_file_path

account_file_path = get_account_file_path()

try:
    size = os.path.getsize(account_file_path)
except FileNotFoundError:
    size = 0
else:
    if size > 0:
        raise Exception(f"The file({account_file_path}) is not empty")

private_key, address = generate_account()
mnemonic = from_private_key(private_key)

account_data = {
    "address": address,
    "private_key": private_key,
    "mnemonic": mnemonic,
}

with open(account_file_path, "w", encoding="utf-8") as f:
    json.dump(account_data, f, ensure_ascii=False, indent=4)

print(f"Generated Account: {address}")
# Fund the account
print(
    f"Go to https://bank.testnet.algorand.network/?account={address} and fund your account."
)

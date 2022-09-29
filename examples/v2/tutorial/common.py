import json
import os
import string
import random
from pprint import pprint

from algosdk.future.transaction import AssetCreateTxn, wait_for_confirmation
from algosdk.v2client.algod import AlgodClient


def get_account_file_path(filename="account.json"):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, filename)
    return file_path


def get_account(filename="account.json"):
    file_path = get_account_file_path(filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            account = json.loads(f.read())
    except FileNotFoundError:
        raise Exception("Please run generate_account.py to generate a test account.")

    return account


def get_assets_file_path(filename="assets.json"):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, filename)
    return file_path


def get_assets(filename="assets.json"):
    file_path = get_account_file_path(filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            assets = json.loads(f.read())
    except FileNotFoundError:
        raise Exception("Please run generate_account.py to generate a test account.")

    return assets


def get_algod():
    # return AlgodClient(
    #     "<TOKEN>", "http://localhost:8080", headers={"User-Agent": "algosdk"}
    # )
    return AlgodClient("", "https://testnet-api.algonode.network")


def create_asset(algod, sender, private_key):
    sp = algod.suggested_params()
    asset_name = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
    )
    max_total = 2**64 - 1
    txn = AssetCreateTxn(
        sender=sender,
        sp=sp,
        total=max_total,
        decimals=6,
        default_frozen=False,
        unit_name=asset_name,
        asset_name=asset_name,
    )
    signed_txn = txn.sign(private_key)
    transaction_id = algod.send_transaction(signed_txn)
    print(f"Asset Creation Transaction ID: {transaction_id}")
    result = wait_for_confirmation(algod, transaction_id)
    print("Asset Creation Result:")
    pprint(result)
    asset_id = result["asset-index"]
    print(f"Created Asset ID: {asset_id}")
    return asset_id

# This sample is provided for demonstration purposes only.
# It is not intended for production use.
# This example does not constitute trading advice.
from pprint import pprint
from urllib.parse import quote_plus

from algosdk.future.transaction import AssetTransferTxn

from examples.v2.tutorial.common import get_account, get_assets
from examples.v2.utils import get_algod
from tinyman.v2.client import TinymanV2TestnetClient
from tinyman.v2.flash_swap import prepare_flash_swap_transactions
from tinyman.v2.formulas import calculate_flash_swap_asset_2_payment_amount

account = get_account()
algod = get_algod()
client = TinymanV2TestnetClient(algod_client=algod, user_address=account["address"])

ASSET_A_ID, ASSET_B_ID = get_assets()["ids"]
ASSET_A = client.fetch_asset(ASSET_A_ID)
ASSET_B = client.fetch_asset(ASSET_B_ID)
pool = client.fetch_pool(ASSET_A_ID, ASSET_B_ID)

suggested_params = algod.suggested_params()
account_info = algod.account_info(account["address"])

for asset in account_info["assets"]:
    if asset["asset-id"] == pool.asset_1.id:
        balance = asset["amount"]

asset_1_loan_amount = 1_000_000
asset_2_loan_amount = 0
asset_1_payment_amount = 0
asset_2_payment_amount = calculate_flash_swap_asset_2_payment_amount(
    asset_1_reserves=pool.asset_1_reserves,
    asset_2_reserves=pool.asset_2_reserves,
    total_fee_share=pool.total_fee_share,
    protocol_fee_ratio=pool.protocol_fee_ratio,
    asset_1_loan_amount=asset_1_loan_amount,
    asset_2_loan_amount=asset_2_loan_amount,
    asset_1_payment_amount=asset_1_payment_amount,
)

# Transfer amount is equal to sum of initial account balance and loan amount
# This transaction demonstrate that you can use the total amount
transfer_amount = balance + asset_1_loan_amount
transactions = [
    AssetTransferTxn(
        sender=account["address"],
        sp=suggested_params,
        receiver=account["address"],
        amt=transfer_amount,
        index=pool.asset_1.id,
    )
]

txn_group = prepare_flash_swap_transactions(
    validator_app_id=pool.validator_app_id,
    asset_1_id=pool.asset_1.id,
    asset_2_id=pool.asset_2.id,
    asset_1_loan_amount=asset_1_loan_amount,
    asset_2_loan_amount=asset_2_loan_amount,
    asset_1_payment_amount=asset_1_payment_amount,
    asset_2_payment_amount=asset_2_payment_amount,
    transactions=transactions,
    suggested_params=suggested_params,
    sender=account["address"],
)

# Sign
txn_group.sign_with_private_key(account["address"], account["private_key"])

# Submit transactions to the network and wait for confirmation
txn_info = txn_group.submit(algod, wait=True)
print("Transaction Info")
pprint(txn_info)

print(
    f"Check the transaction group on Algoexplorer: https://testnet.algoexplorer.io/tx/group/{quote_plus(txn_group.id)}"
)

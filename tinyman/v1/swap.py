import base64
from os import name
import algosdk
from algosdk.future.transaction import ApplicationNoOpTxn, PaymentTxn, AssetTransferTxn, assign_group_id, LogicSigTransaction
from algosdk.v2client.algod import AlgodClient

from .contracts import validator_app_def, get_pool_logicsig
from tinyman.utils import int_to_bytes


def get_swap_with_algo_transactions(client: AlgodClient, sender, validator_app_id, asset1_id, liquidity_asset_id, asset_in_id, asset_in_amount, asset_out_amount, swap_type):
    suggested_params = client.suggested_params()
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, 0)
    pool_address = pool_logicsig.address()

    swap_types = {
        'fixed_input': 'fi',
        'fixed_output': 'fo',
    }

    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=2000,
        ),
        ApplicationNoOpTxn(
            sender=pool_address,
            sp=suggested_params,
            index=validator_app_id,
            app_args=['swap', swap_types[swap_type]],
            accounts=[sender],
            foreign_assets=[asset1_id, liquidity_asset_id],
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=int(asset_in_amount),
            index=asset1_id,
        ) if asset_in_id == asset1_id else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=int(asset_in_amount),
        ),
        AssetTransferTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset_out_amount),
            index=asset1_id,
        ) if asset_in_id == 0 else PaymentTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset_out_amount),
        ),
    ]
    txns = assign_group_id(txns)

    signed_transactions = []
    for txn in txns:
        if txn.sender == pool_address:
            signed_transactions.append(LogicSigTransaction(txn, pool_logicsig))
        else:
            signed_transactions.append(None)
    return txns, signed_transactions
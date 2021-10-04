import base64
from os import name
import algosdk
from algosdk.future.transaction import ApplicationNoOpTxn, PaymentTxn, AssetTransferTxn

from tinyman.utils import TransactionGroup
from .contracts import get_pool_logicsig


def prepare_burn_transactions(validator_app_id, asset1_id, asset2_id, liquidity_asset_id, asset1_amount, asset2_amount, liquidity_asset_amount, sender, suggested_params):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()

    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=3000,
            note='fee',
        ),
        ApplicationNoOpTxn(
            sender=pool_address,
            sp=suggested_params,
            index=validator_app_id,
            app_args=['burn'],
            accounts=[sender],
            foreign_assets=[asset1_id, liquidity_asset_id] if asset2_id == 0 else [asset1_id, asset2_id, liquidity_asset_id],
        ),
        AssetTransferTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset1_amount),
            index=asset1_id,
        ),
        AssetTransferTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset2_amount),
            index=asset2_id,
        ) if asset2_id != 0 else PaymentTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset2_amount),
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=int(liquidity_asset_amount),
            index=liquidity_asset_id,
        ),
    ]
    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicisg(pool_logicsig)
    return txn_group

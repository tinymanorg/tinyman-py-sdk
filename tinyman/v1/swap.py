from typing import Optional

from tinyman.compat import ApplicationNoOpTxn, PaymentTxn, AssetTransferTxn

from tinyman.utils import TransactionGroup
from .contracts import get_pool_logicsig


def prepare_swap_transactions(
    validator_app_id,
    asset1_id,
    asset2_id,
    liquidity_asset_id,
    asset_in_id,
    asset_in_amount,
    asset_out_amount,
    swap_type,
    sender,
    suggested_params,
    app_call_note: Optional[str] = None,
):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()

    swap_types = {
        "fixed-input": "fi",
        "fixed-output": "fo",
    }

    asset_out_id = asset2_id if asset_in_id == asset1_id else asset1_id

    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=2000,
            note="fee",
        ),
        ApplicationNoOpTxn(
            sender=pool_address,
            sp=suggested_params,
            index=validator_app_id,
            app_args=["swap", swap_types[swap_type]],
            accounts=[sender],
            foreign_assets=[asset1_id, liquidity_asset_id]
            if asset2_id == 0
            else [asset1_id, asset2_id, liquidity_asset_id],
            note=app_call_note,
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=int(asset_in_amount),
            index=asset_in_id,
        )
        if asset_in_id != 0
        else PaymentTxn(
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
            index=asset_out_id,
        )
        if asset_out_id != 0
        else PaymentTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset_out_amount),
        ),
    ]

    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicsig(pool_logicsig)
    return txn_group

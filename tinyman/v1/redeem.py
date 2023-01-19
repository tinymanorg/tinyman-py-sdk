from typing import Optional

from tinyman.compat import ApplicationNoOpTxn, PaymentTxn, AssetTransferTxn

from tinyman.utils import TransactionGroup
from .contracts import get_pool_logicsig


def prepare_redeem_transactions(
    validator_app_id,
    asset1_id,
    asset2_id,
    liquidity_asset_id,
    asset_id,
    asset_amount,
    sender,
    suggested_params,
    app_call_note: Optional[str] = None,
):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()

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
            app_args=["redeem"],
            accounts=[sender],
            foreign_assets=[asset1_id, liquidity_asset_id]
            if asset2_id == 0
            else [asset1_id, asset2_id, liquidity_asset_id],
            note=app_call_note,
        ),
        AssetTransferTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset_amount),
            index=asset_id,
        )
        if asset_id != 0
        else PaymentTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=sender,
            amt=int(asset_amount),
        ),
    ]
    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicsig(pool_logicsig)
    return txn_group

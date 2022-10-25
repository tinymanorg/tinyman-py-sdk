from algosdk.future.transaction import ApplicationNoOpTxn, PaymentTxn, AssetTransferTxn

from tinyman.utils import TransactionGroup
from .contracts import get_pool_logicsig


def prepare_redeem_fees_transactions(
    validator_app_id,
    asset1_id,
    asset2_id,
    liquidity_asset_id,
    amount,
    creator,
    sender,
    suggested_params,
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
            app_args=["fees"],
            foreign_assets=[asset1_id, liquidity_asset_id]
            if asset2_id == 0
            else [asset1_id, asset2_id, liquidity_asset_id],
        ),
        AssetTransferTxn(
            sender=pool_address,
            sp=suggested_params,
            receiver=creator,
            amt=int(amount),
            index=liquidity_asset_id,
        ),
    ]
    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicsig(pool_logicsig)
    return txn_group

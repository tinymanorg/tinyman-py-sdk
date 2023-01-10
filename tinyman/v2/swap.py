from typing import Optional

from tinyman.compat import (
    ApplicationNoOpTxn,
    PaymentTxn,
    AssetTransferTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from .constants import (
    SWAP_APP_ARGUMENT,
    FIXED_INPUT_APP_ARGUMENT,
    FIXED_OUTPUT_APP_ARGUMENT,
)
from .contracts import get_pool_logicsig


def prepare_swap_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    asset_in_id: int,
    asset_in_amount: int,
    asset_out_amount: int,
    swap_type: [str, bytes],
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            index=asset_in_id,
            amt=asset_in_amount,
        )
        if asset_in_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_in_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[SWAP_APP_ARGUMENT, swap_type, asset_out_amount],
            foreign_assets=[asset_1_id, asset_2_id],
            accounts=[pool_address],
            note=app_call_note,
        ),
    ]

    if isinstance(swap_type, bytes):
        pass
    elif isinstance(swap_type, str):
        swap_type = swap_type.encode()
    else:
        raise NotImplementedError()

    min_fee = suggested_params.min_fee
    if swap_type == FIXED_INPUT_APP_ARGUMENT:
        # App call contains 1 inner transaction
        app_call_fee = min_fee * 2
    elif swap_type == FIXED_OUTPUT_APP_ARGUMENT:
        # App call contains 2 inner transactions
        app_call_fee = min_fee * 3
    else:
        raise NotImplementedError()

    txns[-1].fee = app_call_fee
    txn_group = TransactionGroup(txns)
    return txn_group

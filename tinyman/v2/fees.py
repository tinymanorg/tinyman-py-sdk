from typing import Optional

from tinyman.compat import (
    ApplicationNoOpTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from tinyman.v2.constants import (
    CLAIM_FEES_APP_ARGUMENT,
    CLAIM_EXTRA_APP_ARGUMENT,
    SET_FEE_APP_ARGUMENT,
)


def prepare_claim_fees_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_address: str,
    fee_collector: str,
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[CLAIM_FEES_APP_ARGUMENT],
            foreign_assets=[asset_1_id, asset_2_id],
            accounts=[pool_address, fee_collector],
            note=app_call_note,
        ),
    ]

    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 3
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_claim_extra_transactions(
    validator_app_id: int,
    asset_id: int,
    address: str,
    fee_collector: str,
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[CLAIM_EXTRA_APP_ARGUMENT],
            foreign_assets=[asset_id],
            accounts=[address, fee_collector],
            note=app_call_note,
        ),
    ]

    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 2
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_fee_transactions(
    validator_app_id: int,
    pool_address: str,
    total_fee_share: int,
    protocol_fee_ratio: int,
    fee_manager: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=fee_manager,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[SET_FEE_APP_ARGUMENT, total_fee_share, protocol_fee_ratio],
            accounts=[pool_address],
            note=app_call_note,
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group

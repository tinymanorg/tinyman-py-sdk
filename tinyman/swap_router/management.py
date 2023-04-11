from typing import Optional

from tinyman.compat import (
    ApplicationNoOpTxn,
    SuggestedParams,
)
from tinyman.swap_router.constants import CLAIM_EXTRA_APP_ARGUMENT, SET_MANAGER_APP_ARGUMENT, SET_EXTRA_COLLECTOR_APP_ARGUMENT
from tinyman.utils import TransactionGroup


def prepare_claim_extra_transactions(
    router_app_id: int,
    asset_ids: [int],
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:

    claim_extra_app_call = ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=router_app_id,
        app_args=[CLAIM_EXTRA_APP_ARGUMENT],
        foreign_assets=asset_ids,
        note=app_call_note
    )
    min_fee = suggested_params.min_fee
    inner_transaction_count = len(asset_ids)
    claim_extra_app_call.fee = min_fee * (1 + inner_transaction_count)

    txn_group = TransactionGroup([claim_extra_app_call])
    return txn_group


def prepare_set_set_manager_transactions(
    router_app_id: int,
    manager: str,
    new_manager: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=manager,
            sp=suggested_params,
            index=router_app_id,
            app_args=[SET_MANAGER_APP_ARGUMENT],
            accounts=[new_manager],
            note=app_call_note,
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_extra_collector_transactions(
    router_app_id: int,
    manager: str,
    new_extra_collector: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=manager,
            sp=suggested_params,
            index=router_app_id,
            app_args=[SET_EXTRA_COLLECTOR_APP_ARGUMENT],
            accounts=[new_extra_collector],
            note=app_call_note,
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group



from algosdk.future.transaction import (
    ApplicationNoOpTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from tinyman.v2.constants import (
    SET_FEE_COLLECTOR_APP_ARGUMENT,
    SET_FEE_SETTER_APP_ARGUMENT,
    SET_FEE_MANAGER_APP_ARGUMENT,
)


def prepare_set_fee_collector_transactions(
    validator_app_id: int,
    fee_manager: str,
    new_fee_collector: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=fee_manager,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[SET_FEE_COLLECTOR_APP_ARGUMENT],
            accounts=[new_fee_collector],
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_fee_setter_transactions(
    validator_app_id: int,
    fee_manager: str,
    new_fee_setter: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=fee_manager,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[SET_FEE_SETTER_APP_ARGUMENT],
            accounts=[new_fee_setter],
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_fee_manager_transactions(
    validator_app_id: int,
    fee_manager: str,
    new_fee_manager: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    txns = [
        ApplicationNoOpTxn(
            sender=fee_manager,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[SET_FEE_MANAGER_APP_ARGUMENT],
            accounts=[new_fee_manager],
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group

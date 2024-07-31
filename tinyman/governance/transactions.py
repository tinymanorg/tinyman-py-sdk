import uuid
from typing import Optional, Union

from algosdk import transaction
from algosdk.encoding import decode_address

from tinyman.compat import SuggestedParams
from tinyman.constants import MAX_APP_TOTAL_TXN_REFERENCES
from tinyman.governance.constants import INCREASE_BUDGET_APP_ARGUMENT, GET_BOX_APP_ARGUMENT, SET_MANAGER_APP_ARGUMENT, SET_PROPOSAL_MANAGER_APP_ARGUMENT, SET_VOTING_DELAY_APP_ARGUMENT, SET_VOTING_DURATION_APP_ARGUMENT
from tinyman.utils import TransactionGroup


def _prepare_budget_increase_transaction(
        sender: str,
        sp: transaction.SuggestedParams,
        index: int,
        extra_app_args: Optional[list[Union[bytes, bytearray, str, int]]] = None,
        foreign_apps: list[int] = None,
        boxes: list[(int, bytes)] = None
):
    """
    It increases opcode budget and box read budget.
    """
    if foreign_apps is None:
        foreign_apps = []

    if boxes is None:
        boxes = []

    # MaxAppTotalTxnReferences (Max number of foreign accounts + ASAs + applications + box storage)
    boxes = boxes + ([(0, "")] * ((MAX_APP_TOTAL_TXN_REFERENCES - len(foreign_apps)) - len(boxes)))

    return transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=sp,
        index=index,
        app_args=[INCREASE_BUDGET_APP_ARGUMENT] + (extra_app_args if extra_app_args else []),
        foreign_apps=foreign_apps,
        boxes=boxes,
        # Make transactions unique to avoid "transaction already in ledger" error
        note=uuid.uuid4().bytes
    )


def _prepare_get_box_transaction(
        app_id: int,
        sender: str,
        box_name: Union[bytes, bytearray, str, int],
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[
                GET_BOX_APP_ARGUMENT,
                box_name
            ],
            boxes=[
                (app_id, box_name),
            ],
            note=app_call_note,
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def _prepare_set_manager_transactions(
        app_id: int,
        sender: str,
        new_manager_address: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only proposal manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[SET_MANAGER_APP_ARGUMENT, decode_address(new_manager_address)],
            note=app_call_note
        ),
    ]

    txn_group = TransactionGroup(txns)
    return txn_group


def _prepare_set_proposal_manager_transactions(
        app_id: int,
        sender: str,
        new_manager_address: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[SET_PROPOSAL_MANAGER_APP_ARGUMENT, decode_address(new_manager_address)],
            note=app_call_note
        ),
    ]

    txn_group = TransactionGroup(txns)
    return txn_group


def _prepare_set_voting_delay_transactions(
        app_id: int,
        sender: str,
        new_voting_delay: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[SET_VOTING_DELAY_APP_ARGUMENT, new_voting_delay],
            note=app_call_note
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def _prepare_set_voting_duration_transactions(
        app_id: int,
        sender: str,
        new_voting_duration: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[SET_VOTING_DURATION_APP_ARGUMENT, new_voting_duration],
            note=app_call_note
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group

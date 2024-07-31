from typing import Optional

from algosdk import transaction
from algosdk.constants import ZERO_ADDRESS
from algosdk.encoding import decode_address
from algosdk.logic import get_application_address

from tinyman.compat import SuggestedParams
from tinyman.governance.proposal_voting.constants import PROPOSAL_BOX_COST, ACCOUNT_ATTENDANCE_SHEET_BOX_SIZE, ATTENDANCE_SHEET_BOX_COST, CREATE_PROPOSAL_APP_ARGUMENT, \
    CAST_VOTE_APP_ARGUMENT, GET_PROPOSAL_APP_ARGUMENT, HAS_VOTED_APP_ARGUMENT, APPROVE_PROPOSAL_APP_ARGUMENT, CANCEL_PROPOSAL_APP_ARGUMENT, EXECUTE_PROPOSAL_APP_ARGUMENT, \
    DISABLE_APPROVAL_REQUIREMENT_APP_ARGUMENT, SET_PROPOSAL_THRESHOLD_APP_ARGUMENT, SET_QUORUM_THRESHOLD_APP_ARGUMENT, GET_PROPOSAL_STATE_APP_ARGUMENT, SET_PROPOSAL_THRESHOLD_NUMERATOR_APP_ARGUMENT, \
    CREATE_PROPOSAL_DEFAULT_EXECUTION_HASH_ARGUMENT
from tinyman.governance.proposal_voting.storage import Proposal
from tinyman.governance.proposal_voting.storage import get_proposal_box_name, get_attendance_sheet_box_name
from tinyman.governance.transactions import _prepare_set_manager_transactions, _prepare_set_proposal_manager_transactions, _prepare_set_voting_delay_transactions, \
    _prepare_set_voting_duration_transactions
from tinyman.governance.vault.constants import ACCOUNT_POWER_BOX_ARRAY_LEN
from tinyman.governance.vault.storage import VaultAppGlobalState, get_account_state_box_name, get_account_power_box_name
from tinyman.governance.vault.storage import get_total_power_box_name
from tinyman.utils import TransactionGroup


def generate_proposal_metadata(
        title: str,
        description: str,
        category: str,
        discussion_url: str,
        poll_url: str,
):
    # keys are sorted.
    metadata = dict(
        category=category,
        description=description,
        discussion_url=discussion_url,
        poll_url=poll_url,
        title=title,
    )
    for key, value in metadata.items():
        metadata[key] = value.strip()
    return metadata


def prepare_create_proposal_transactions(
        proposal_voting_app_id: int,
        vault_app_id: int,
        sender: str,
        proposal_id: str,
        vault_app_global_state: VaultAppGlobalState,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
        execution_hash: Optional[str] = None,
        executor: Optional[str] = None,
):
    proposal_box_name = get_proposal_box_name(proposal_id)
    account_state_box_name = get_account_state_box_name(address=sender)
    last_total_power_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)

    txns = [
        transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(proposal_voting_app_id),
            amt=PROPOSAL_BOX_COST,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[CREATE_PROPOSAL_APP_ARGUMENT, proposal_id, execution_hash or CREATE_PROPOSAL_DEFAULT_EXECUTION_HASH_ARGUMENT, executor or decode_address(ZERO_ADDRESS)],
            foreign_apps=[vault_app_id],
            boxes=[
                (proposal_voting_app_id, proposal_box_name),
                (vault_app_id, account_state_box_name),
                (vault_app_id, last_total_power_box_name)
            ],
            note=app_call_note
        )
    ]

    # 2 inner txns
    txns[1].fee *= 3
    return TransactionGroup(txns)


def prepare_cast_vote_transactions(
        proposal_voting_app_id: int,
        vault_app_id: int,
        sender: str,
        proposal_id: str,
        proposal: Proposal,
        vote: int,
        account_power_index: int,
        create_attendance_sheet_box: bool,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    assert vote in [0, 1, 2]

    account_power_box_index = account_power_index // ACCOUNT_POWER_BOX_ARRAY_LEN
    account_attendance_box_index = proposal.index // (ACCOUNT_ATTENDANCE_SHEET_BOX_SIZE * 8)
    boxes = [
        (proposal_voting_app_id, get_proposal_box_name(proposal_id)),
        (proposal_voting_app_id, get_attendance_sheet_box_name(sender, account_attendance_box_index)),
        (vault_app_id, get_account_state_box_name(address=sender)),
        (vault_app_id, get_account_power_box_name(address=sender, box_index=account_power_box_index)),
        (vault_app_id, get_account_power_box_name(address=sender, box_index=account_power_box_index + 1)),
    ]

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[CAST_VOTE_APP_ARGUMENT, proposal_id, vote, account_power_index],
            foreign_apps=[vault_app_id],
            boxes=boxes,
            note=app_call_note
        ),
    ]
    # 1 inner txn
    txns[0].fee *= 2

    if create_attendance_sheet_box:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(proposal_voting_app_id),
            amt=ATTENDANCE_SHEET_BOX_COST,
        )
        txns.insert(0, minimum_balance_payment)

    return TransactionGroup(txns)


def prepare_get_proposal_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    proposal_box_name = get_proposal_box_name(proposal_id)

    boxes = [
        (proposal_voting_app_id, proposal_box_name),
    ]
    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[GET_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=boxes,
            note=app_call_note
        ),
    ]
    return TransactionGroup(txn_group)


def prepare_get_proposal_state_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    proposal_box_name = get_proposal_box_name(proposal_id)

    boxes = [
        (proposal_voting_app_id, proposal_box_name),
    ]
    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[GET_PROPOSAL_STATE_APP_ARGUMENT, proposal_id],
            boxes=boxes,
            note=app_call_note
        ),
    ]
    return TransactionGroup(txn_group)


def prepare_has_voted_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        proposal: Proposal,
        suggested_params: SuggestedParams,
        address_to_check: Optional[str] = None,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    if address_to_check is None:
        address_to_check = sender

    proposal_box_name = get_proposal_box_name(proposal_id)
    account_attendance_box_index = proposal.index // (ACCOUNT_ATTENDANCE_SHEET_BOX_SIZE * 8)

    boxes = [
        (proposal_voting_app_id, proposal_box_name),
        (proposal_voting_app_id, get_attendance_sheet_box_name(address_to_check, account_attendance_box_index)),
    ]

    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[HAS_VOTED_APP_ARGUMENT, proposal_id, decode_address(address_to_check)],
            boxes=boxes,
            note=app_call_note
        ),
    ]
    return TransactionGroup(txn_group)


def prepare_approve_proposal_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    proposal_box_name = get_proposal_box_name(proposal_id)
    boxes = [
        (proposal_voting_app_id, proposal_box_name),
    ]
    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[APPROVE_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=boxes,
            note=app_call_note
        )
    ]
    return TransactionGroup(txn_group)


def prepare_cancel_proposal_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    proposal_box_name = get_proposal_box_name(proposal_id)
    boxes = [
        (proposal_voting_app_id, proposal_box_name),
    ]
    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[CANCEL_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=boxes,
            note=app_call_note
        )
    ]
    return TransactionGroup(txn_group)


def prepare_execute_proposal_transactions(
        proposal_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    proposal_box_name = get_proposal_box_name(proposal_id)
    boxes = [
        (proposal_voting_app_id, proposal_box_name),
    ]
    txn_group = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[EXECUTE_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=boxes,
            note=app_call_note
        )
    ]
    return TransactionGroup(txn_group)


def prepare_set_manager_transactions(
        proposal_voting_app_id: int,
        **kwargs
):
    # Only proposal manager can call this method.
    return _prepare_set_manager_transactions(app_id=proposal_voting_app_id, **kwargs)


def prepare_set_proposal_manager_transactions(
        proposal_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_proposal_manager_transactions(app_id=proposal_voting_app_id, **kwargs)


def prepare_disable_approval_requirement_transactions(
        proposal_voting_app_id: int,
        sender: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[DISABLE_APPROVAL_REQUIREMENT_APP_ARGUMENT],
            note=app_call_note
        ),
    ]

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_voting_delay_transactions(
        proposal_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_voting_delay_transactions(app_id=proposal_voting_app_id, **kwargs)


def prepare_set_voting_duration_transactions(
        proposal_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_voting_duration_transactions(app_id=proposal_voting_app_id, **kwargs)


def prepare_set_proposal_threshold_transactions(
        proposal_voting_app_id: int,
        sender: str,
        new_proposal_threshold: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[SET_PROPOSAL_THRESHOLD_APP_ARGUMENT, new_proposal_threshold],
            note=app_call_note
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_proposal_threshold_numerator_transactions(
        proposal_voting_app_id: int,
        sender: str,
        new_proposal_threshold_numerator: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[SET_PROPOSAL_THRESHOLD_NUMERATOR_APP_ARGUMENT, new_proposal_threshold_numerator],
            note=app_call_note
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_quorum_threshold_transactions(
        proposal_voting_app_id: int,
        sender: str,
        new_quorum_threshold: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # Only manager can call this method.
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=proposal_voting_app_id,
            app_args=[SET_QUORUM_THRESHOLD_APP_ARGUMENT, new_quorum_threshold],
            note=app_call_note
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group

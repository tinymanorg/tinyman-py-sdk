from typing import Optional

from algosdk import transaction
from algosdk.logic import get_application_address

from tinyman.compat import SuggestedParams
from tinyman.governance.staking_voting.constants import STAKING_PROPOSAL_BOX_COST, STAKING_VOTE_BOX_COST, STAKING_ATTENDANCE_BOX_COST, MAX_OPTION_COUNT, \
    STAKING_PROPOSAL_CATEGORY, CREATE_PROPOSAL_APP_ARGUMENT, CANCEL_PROPOSAL_APP_ARGUMENT, CAST_VOTE_APP_ARGUMENT
from tinyman.governance.staking_voting.storage import StakingDistributionProposal, get_staking_attendance_sheet_box_name, get_staking_distribution_proposal_box_name, \
    get_staking_vote_box_name
from tinyman.governance.transactions import _prepare_budget_increase_transaction, _prepare_get_box_transaction, _prepare_set_manager_transactions, \
    _prepare_set_proposal_manager_transactions, _prepare_set_voting_delay_transactions, _prepare_set_voting_duration_transactions
from tinyman.governance.vault.constants import ACCOUNT_POWER_BOX_ARRAY_LEN
from tinyman.governance.vault.storage import get_account_state_box_name, get_account_power_box_name
from tinyman.utils import int_to_bytes, TransactionGroup


def generate_staking_distribution_proposal_metadata(
        title: str,
        description: str,
        staking_program_start_time: int,
        staking_program_end_time: int,
        staking_program_cycle_duration: int,
        staking_program_reward_asset: int,
):
    # keys are sorted.
    metadata = dict(
        category=STAKING_PROPOSAL_CATEGORY,
        description=description,
        staking_program=dict(
            cycle_duration=staking_program_cycle_duration,
            end_date=staking_program_end_time,
            reward_asset=staking_program_reward_asset,
            start_date=staking_program_start_time,
        ),
        title=title,
    )
    for key, value in metadata.items():
        if isinstance(value, str):
            metadata[key] = value.strip()
    return metadata


def prepare_create_staking_distribution_proposal_transactions(
        staking_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    # Only proposal manager can call this method.
    proposal_box_name = get_staking_distribution_proposal_box_name(proposal_id)

    txns = [
        transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(staking_voting_app_id),
            amt=STAKING_PROPOSAL_BOX_COST,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=staking_voting_app_id,
            app_args=[CREATE_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=[
                (staking_voting_app_id, proposal_box_name),
            ],
            note=app_call_note
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_cancel_staking_distribution_proposal_transactions(
        staking_voting_app_id: int,
        sender: str,
        proposal_id: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    # Only proposal manager can call this method.
    proposal_box_name = get_staking_distribution_proposal_box_name(proposal_id)
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=staking_voting_app_id,
            app_args=[CANCEL_PROPOSAL_APP_ARGUMENT, proposal_id],
            boxes=[
                (staking_voting_app_id, proposal_box_name),
            ],
            note=app_call_note
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_cast_vote_for_staking_distribution_proposal_transactions(
        staking_voting_app_id: int,
        vault_app_id: int,
        sender: str,
        proposal_id: str,
        proposal: StakingDistributionProposal,
        votes: list[int],
        asset_ids: list[int],
        account_power_index: int,
        app_box_names: list[bytes],
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None
):
    # All governors who have voting power at the creation time of can vote
    assert (len(votes) == len(asset_ids))
    assert len(asset_ids) <= MAX_OPTION_COUNT
    assert sum(votes) == 100

    arg_votes = b"".join([int_to_bytes(vote) for vote in votes])
    arg_asset_ids = b"".join([int_to_bytes(asset_id) for asset_id in asset_ids])

    proposal_box_name = get_staking_distribution_proposal_box_name(proposal_id)

    account_attendance_sheet_box_index = proposal.index // (1024 * 8)
    account_attendance_sheet_box_name = get_staking_attendance_sheet_box_name(address=sender, box_index=account_attendance_sheet_box_index)
    create_attendance_sheet_box = account_attendance_sheet_box_name not in app_box_names

    account_state_box_name = get_account_state_box_name(address=sender)
    account_power_box_index = account_power_index // ACCOUNT_POWER_BOX_ARRAY_LEN
    account_power_box_name = get_account_power_box_name(address=sender, box_index=account_power_box_index)
    next_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_power_box_index + 1)

    new_asset_count = 0
    vote_boxes = []
    for asset_id in asset_ids:
        vote_box_name = get_staking_vote_box_name(proposal.index, asset_id)
        vote_boxes.append((staking_voting_app_id, vote_box_name))
        if vote_box_name not in app_box_names:
            new_asset_count += 1

    boxes = [
        (staking_voting_app_id, proposal_box_name),
        (staking_voting_app_id, account_attendance_sheet_box_name),
        *vote_boxes,
        (vault_app_id, account_state_box_name),
        (vault_app_id, account_power_box_name),
        (vault_app_id, next_account_power_box_name),
    ]
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=staking_voting_app_id,
            app_args=[CAST_VOTE_APP_ARGUMENT, proposal_id, arg_votes, arg_asset_ids, account_power_index],
            foreign_apps=[vault_app_id],
            boxes=boxes[:7],
            note=app_call_note
        ),
    ]
    txns[0].fee *= 2

    if len(boxes) >= 7:
        txns.append(
            _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, foreign_apps=[staking_voting_app_id], boxes=boxes[7:14]),
        )
    if len(boxes) >= 14:
        txns.append(
            _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, foreign_apps=[staking_voting_app_id], boxes=boxes[14:]),
        )

    payment_amount = (create_attendance_sheet_box * STAKING_ATTENDANCE_BOX_COST) + (new_asset_count * STAKING_VOTE_BOX_COST)
    if payment_amount:
        txns = [
            transaction.PaymentTxn(
                sender=sender,
                sp=suggested_params,
                receiver=get_application_address(staking_voting_app_id),
                amt=payment_amount,
            )
        ] + txns

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_manager_transactions(
        staking_voting_app_id: int,
        **kwargs
):
    # Only proposal manager can call this method.
    return _prepare_set_manager_transactions(app_id=staking_voting_app_id, **kwargs)


def prepare_set_proposal_manager_transactions(
        staking_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_proposal_manager_transactions(app_id=staking_voting_app_id, **kwargs)


def prepare_set_voting_delay_transactions(
        staking_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_voting_delay_transactions(app_id=staking_voting_app_id, **kwargs)


def prepare_set_voting_duration_transactions(
        staking_voting_app_id: int,
        **kwargs
):
    # Only manager can call this method.
    return _prepare_set_voting_duration_transactions(app_id=staking_voting_app_id, **kwargs)


def prepare_get_box_transaction(
        staking_voting_app_id: int,
        **kwargs
) -> TransactionGroup:
    return _prepare_get_box_transaction(app_id=staking_voting_app_id, **kwargs)

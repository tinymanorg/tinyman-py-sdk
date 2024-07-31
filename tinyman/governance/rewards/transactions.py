from typing import Optional

from algosdk import transaction
from algosdk.logic import get_application_address

from tinyman.compat import SuggestedParams
from tinyman.constants import MAX_APP_PROGRAM_COST
from tinyman.governance.rewards.constants import REWARDS_APP_MINIMUM_BALANCE_REQUIREMENT, REWARD_HISTORY_BOX_ARRAY_LEN, REWARD_CLAIM_SHEET_BOX_SIZE, REWARD_CLAIM_SHEET_BOX_COST, REWARD_PERIOD_BOX_COST, REWARD_PERIOD_BOX_ARRAY_LEN, REWARD_HISTORY_BOX_COST, INIT_APP_ARGUMENT, SET_REWARD_AMOUNT_APP_ARGUMENT, CREATE_REWARD_PERIOD_APP_ARGUMENT, CLAIM_REWARDS_APP_ARGUMENT, SET_REWARDS_MANAGER_APP_ARGUMENT
from tinyman.governance.rewards.storage import RewardsAppGlobalState, get_reward_history_box_name, get_account_reward_claim_sheet_box_name, get_reward_period_box_name
from tinyman.governance.transactions import _prepare_budget_increase_transaction, _prepare_get_box_transaction, _prepare_set_manager_transactions
from tinyman.governance.vault.constants import ACCOUNT_POWER_BOX_ARRAY_LEN, TOTAL_POWER_BOX_ARRAY_LEN
from tinyman.governance.vault.storage import get_total_power_box_name, get_account_state_box_name, get_account_power_box_name
from tinyman.utils import TransactionGroup, int_to_bytes
from algosdk.encoding import decode_address


def prepare_init_transactions(
        rewards_app_id: int,
        tiny_asset_id: int,
        reward_amount: int,
        sender: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    # Boxes
    reward_histories_box_name = get_reward_history_box_name(box_index=0)
    boxes = [
        (rewards_app_id, reward_histories_box_name),
    ]

    payment_txn = transaction.PaymentTxn(
        sender=sender,
        sp=suggested_params,
        receiver=get_application_address(rewards_app_id),
        amt=REWARDS_APP_MINIMUM_BALANCE_REQUIREMENT,
    )
    application_call_txn = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=rewards_app_id,
        app_args=[
            INIT_APP_ARGUMENT,
            reward_amount
        ],
        foreign_assets=[
            tiny_asset_id
        ],
        boxes=boxes,
        note=app_call_note
    )
    application_call_txn.fee *= 2

    txns = [payment_txn, application_call_txn]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_reward_amount_transactions(
        rewards_app_id: int,
        rewards_app_global_state: RewardsAppGlobalState,
        reward_amount: int,
        sender: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    # Boxes
    reward_history_index = rewards_app_global_state.reward_history_count
    reward_history_box_index = reward_history_index // REWARD_HISTORY_BOX_ARRAY_LEN
    reward_histories_box_name = get_reward_history_box_name(box_index=reward_history_box_index)
    boxes = [
        (rewards_app_id, reward_histories_box_name),
    ]

    application_call_txn = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=rewards_app_id,
        app_args=[
            SET_REWARD_AMOUNT_APP_ARGUMENT,
            reward_amount
        ],
        boxes=boxes,
        note=app_call_note
    )
    txns = [application_call_txn]

    if not rewards_app_global_state.free_reward_history_space_count:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(rewards_app_id),
            amt=REWARD_HISTORY_BOX_COST,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_create_reward_period_transactions(
        rewards_app_id: int,
        vault_app_id: int,
        sender: str,
        rewards_app_global_state: RewardsAppGlobalState,
        reward_history_index: int,
        total_power_period_start_index: int,
        total_power_period_end_index: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,

) -> TransactionGroup:
    total_power_period_start_box_index = total_power_period_start_index // TOTAL_POWER_BOX_ARRAY_LEN
    total_power_period_end_box_index = total_power_period_end_index // TOTAL_POWER_BOX_ARRAY_LEN
    reward_history_box_index = reward_history_index // REWARD_HISTORY_BOX_ARRAY_LEN

    reward_period_index = rewards_app_global_state.reward_period_count
    reward_period_box_index = reward_period_index // REWARD_PERIOD_BOX_ARRAY_LEN
    reward_period_array_index = reward_period_index % REWARD_PERIOD_BOX_ARRAY_LEN

    total_power_period_start_box_name = get_total_power_box_name(box_index=total_power_period_start_box_index)
    total_power_period_end_box_name = get_total_power_box_name(box_index=total_power_period_end_box_index)
    total_power_next_box_name = get_total_power_box_name(box_index=total_power_period_end_box_index + 1)
    reward_history_box_name = get_reward_history_box_name(box_index=reward_history_box_index)
    reward_period_box_name = get_reward_period_box_name(box_index=reward_period_box_index)

    boxes = [
        (rewards_app_id, reward_history_box_name),
        (rewards_app_id, reward_period_box_name),
        (vault_app_id, total_power_period_start_box_name),
        (vault_app_id, total_power_period_end_box_name),
        (vault_app_id, total_power_next_box_name),
    ]
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=rewards_app_id,
            app_args=[
                CREATE_REWARD_PERIOD_APP_ARGUMENT,
                total_power_period_start_index,
                total_power_period_end_index,
                reward_history_index
            ],
            foreign_apps=[vault_app_id],
            boxes=boxes,
            note=app_call_note,
        ),
    ]
    txns[0].fee *= 2

    if reward_period_array_index == 0:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(rewards_app_id),
            amt=REWARD_PERIOD_BOX_COST,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_claim_reward_transactions(
        rewards_app_id: int,
        vault_app_id: int,
        tiny_asset_id: int,
        sender: str,
        period_index_start: int,
        period_count: int,
        account_power_indexes: list[int],
        create_reward_claim_sheet: bool,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    account_state_box_name = get_account_state_box_name(address=sender)
    assert period_count <= 104

    reward_period_boxes = set()
    account_reward_claim_sheet_boxes = set()
    for period_index in range(period_index_start, period_index_start + period_count):
        reward_period_box_index = period_index // REWARD_PERIOD_BOX_ARRAY_LEN
        box_name = get_reward_period_box_name(box_index=reward_period_box_index)
        reward_period_boxes.add((rewards_app_id, box_name))

        account_reward_claim_sheet_box_index = period_index // (REWARD_CLAIM_SHEET_BOX_SIZE * 8)
        box_name = get_account_reward_claim_sheet_box_name(address=sender, box_index=account_reward_claim_sheet_box_index)
        account_reward_claim_sheet_boxes.add((rewards_app_id, box_name))

    account_power_boxes = set()
    for account_power_index in account_power_indexes:
        account_power_box_index = account_power_index // ACCOUNT_POWER_BOX_ARRAY_LEN
        box_name = get_account_power_box_name(address=sender, box_index=account_power_box_index)
        account_power_boxes.add((vault_app_id, box_name))
        box_name = get_account_power_box_name(address=sender, box_index=account_power_box_index + 1)
        account_power_boxes.add((vault_app_id, box_name))

    boxes = [
        (vault_app_id, account_state_box_name),
        *account_reward_claim_sheet_boxes,  # MAX 2
        *reward_period_boxes,           # MAX 2
        *account_power_boxes,   # MAX 5
    ]
    assert len(boxes) < 11

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=rewards_app_id,
            app_args=[
                CLAIM_REWARDS_APP_ARGUMENT,
                period_index_start,
                period_count,
                b''.join([int_to_bytes(i) for i in account_power_indexes])
            ],
            foreign_apps=[vault_app_id],
            foreign_assets=[tiny_asset_id],
            boxes=boxes[:6],    # Max total txn reference is 8 (MaxAppTotalTxnReferences), remaining is 2 for boxes.
            note=app_call_note,
        ),
    ]
    txns[0].fee *= (period_count + 2)

    increase_budget_txn_count = 0
    required_opcode_budget = 92 + 865 * period_count

    opcode_budget = MAX_APP_PROGRAM_COST + MAX_APP_PROGRAM_COST * period_count
    if required_opcode_budget > opcode_budget:
        increase_budget_txn_count = ((required_opcode_budget - opcode_budget) // 666) + 1

    if increase_budget_txn_count or boxes[6:]:
        budget_increase_txn = _prepare_budget_increase_transaction(
            sender,
            extra_app_args=[max(increase_budget_txn_count - 1, 0)],
            sp=suggested_params,
            index=rewards_app_id,
            foreign_apps=[vault_app_id],
            boxes=boxes[6:]
        )
        budget_increase_txn.fee *= max(increase_budget_txn_count, 1)
        txns.insert(0, budget_increase_txn)

    if create_reward_claim_sheet:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(rewards_app_id),
            amt=REWARD_CLAIM_SHEET_BOX_COST,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_set_manager_transactions(
        rewards_app_id: int,
        **kwargs
) -> TransactionGroup:
    return _prepare_set_manager_transactions(app_id=rewards_app_id, **kwargs)


def prepare_set_rewards_manager_transactions(
        rewards_app_id: int,
        sender: str,
        new_manager_address: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=rewards_app_id,
            app_args=[SET_REWARDS_MANAGER_APP_ARGUMENT, decode_address(new_manager_address)],
            note=app_call_note,
        ),
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_box_transaction(
        rewards_app_id: int,
        **kwargs
) -> TransactionGroup:
    return _prepare_get_box_transaction(app_id=rewards_app_id, **kwargs)

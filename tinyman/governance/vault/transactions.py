import math
import time
from typing import Optional

from algosdk import transaction
from algosdk.encoding import decode_address
from algosdk.logic import get_application_address

from tinyman.compat import SuggestedParams
from tinyman.constants import MAX_APP_PROGRAM_COST, MAX_APP_TOTAL_TXN_REFERENCES
from tinyman.governance.constants import WEEK
from tinyman.governance.transactions import _prepare_budget_increase_transaction, _prepare_get_box_transaction
from tinyman.governance.vault.exceptions import InsufficientLockAmount, InvalidLockEndTime
from tinyman.governance.vault.storage import get_total_power_box_name, get_account_state_box_name, get_account_power_box_name, get_slope_change_box_name, get_power_index_at, \
    VaultAppGlobalState, AccountState, TotalPower, AccountPower, SlopeChange
from tinyman.governance.vault.constants import VAULT_APP_MINIMUM_BALANCE_REQUIREMENT, TOTAL_POWER_BOX_ARRAY_LEN, ACCOUNT_POWER_BOX_ARRAY_LEN, ACCOUNT_STATE_BOX_COST, \
    SLOPE_CHANGE_BOX_COST, ACCOUNT_POWER_BOX_COST, TOTAL_POWER_BOX_COST, MIN_LOCK_AMOUNT, MIN_LOCK_AMOUNT_INCREMENT, INIT_APP_ARGUMENT, CREATE_LOCK_APP_ARGUMENT, \
    CREATE_CHECKPOINTS_APP_ARGUMENT, INCREASE_LOCK_AMOUNT_APP_ARGUMENT, EXTEND_LOCK_END_TIME_APP_ARGUMENT, WITHDRAW_APP_ARGUMENT, GET_TINY_POWER_OF_APP_ARGUMENT, \
    GET_TINY_POWER_OF_AT_APP_ARGUMENT, GET_TOTAL_TINY_POWER_APP_ARGUMENT, GET_TOTAL_TINY_POWER_AT_APP_ARGUMENT, GET_TOTAL_CUMULATIVE_POWER_AT_APP_ARGUMENT, GET_CUMULATIVE_POWER_OF_AT_APP_ARGUMENT, \
    GET_ACCOUNT_CUMULATIVE_POWER_DELTA_APP_PREFIX, GET_TOTAL_CUMULATIVE_POWER_DELTA_APP_PREFIX,DELETE_ACCOUNT_POWER_BOXES_APP_ARGUMENT, DELETE_ACCOUNT_STATE_APP_ARGUMENT
from tinyman.governance.vault.utils import get_new_total_power_timestamps
from tinyman.utils import TransactionGroup


def prepare_init_transactions(
        vault_app_id: int,
        tiny_asset_id: int,
        sender: str,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    """
    This method must be called once to initialize the checkpoints and opt-in to TINY after the deployment.
    """

    total_powers_box_name = get_total_power_box_name(box_index=0)
    boxes = [
        (vault_app_id, total_powers_box_name),
    ]
    txns = [
        transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=VAULT_APP_MINIMUM_BALANCE_REQUIREMENT,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[
                INIT_APP_ARGUMENT,
            ],
            foreign_assets=[
                tiny_asset_id
            ],
            boxes=boxes,
            note=app_call_note,
        ),
        _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id),
    ]
    txns[1].fee *= 2    # opt-in inner txn
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_create_lock_transactions(
        vault_app_id: int,
        tiny_asset_id: int,
        sender: str,
        locked_amount: int,
        lock_end_time: int,
        vault_app_global_state: VaultAppGlobalState,
        account_state: Optional[AccountState],
        slope_change_at_lock_end_time: Optional[SlopeChange],
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    if locked_amount < MIN_LOCK_AMOUNT:
        raise InsufficientLockAmount()

    if lock_end_time % WEEK:
        raise InvalidLockEndTime()

    # Boxes
    account_state_box_name = get_account_state_box_name(address=sender)
    last_total_power_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)
    next_total_power_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index + 1)
    boxes = [
        (vault_app_id, account_state_box_name),
        (vault_app_id, last_total_power_box_name),
        # Always pass the next total power box ref, other transactions may increase the total power count.
        (vault_app_id, next_total_power_box_name),
    ]
    if account_state is None:
        account_power_box_name = get_account_power_box_name(address=sender, box_index=0)
        boxes.append((vault_app_id, account_power_box_name))
    else:
        last_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index)
        boxes.append((vault_app_id, last_account_power_box_name))

        if not account_state.free_account_power_space_count:
            next_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index + 1)
            boxes.append((vault_app_id, next_account_power_box_name))

    # slope change will be updated or created for lock end time
    slope_change_box_name = get_slope_change_box_name(timestamp=lock_end_time)
    boxes.append((vault_app_id, slope_change_box_name))

    # contract will create weekly checkpoints automatically
    new_total_power_timestamps = get_new_total_power_timestamps(vault_app_global_state.last_total_power_timestamp, int(time.time()))
    new_total_power_count = len(new_total_power_timestamps)
    for timestamp in new_total_power_timestamps:
        if timestamp % WEEK == 0:
            slope_change_box_name = get_slope_change_box_name(timestamp=timestamp)
            boxes.append((vault_app_id, slope_change_box_name))

    # Min Balance
    min_balance_increase = 0
    if account_state is None:
        min_balance_increase += ACCOUNT_STATE_BOX_COST
        min_balance_increase += ACCOUNT_POWER_BOX_COST
    else:
        if not account_state.free_account_power_space_count:
            min_balance_increase += ACCOUNT_POWER_BOX_COST

    if new_total_power_count > vault_app_global_state.free_total_power_space_count:
        min_balance_increase += TOTAL_POWER_BOX_COST

    if slope_change_at_lock_end_time is None:
        min_balance_increase += SLOPE_CHANGE_BOX_COST

    txns = [
        transaction.AssetTransferTxn(
            index=tiny_asset_id,
            sender=sender,
            receiver=get_application_address(vault_app_id),
            amt=locked_amount,
            sp=suggested_params,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[
                CREATE_LOCK_APP_ARGUMENT,
                lock_end_time,
            ],
            boxes=boxes[:MAX_APP_TOTAL_TXN_REFERENCES],
            note=app_call_note
        ),
        _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, boxes=boxes[MAX_APP_TOTAL_TXN_REFERENCES:])
    ]

    if min_balance_increase:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=min_balance_increase,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_create_checkpoints_transactions(
        vault_app_id: int,
        sender: str,
        vault_app_global_state: VaultAppGlobalState,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    # Boxes
    boxes = [
        (vault_app_id, get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)),
        (vault_app_id, get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index + 1)),
    ]

    new_total_power_timestamps = get_new_total_power_timestamps(vault_app_global_state.last_total_power_timestamp, int(time.time()))
    new_total_power_timestamps = new_total_power_timestamps[:9]   # a contract call can create maximum 9 total_powers
    new_total_power_count = len(new_total_power_timestamps)

    for timestamp in new_total_power_timestamps:
        if timestamp % WEEK == 0:
            slope_change_box_name = get_slope_change_box_name(timestamp=timestamp)
            boxes.append((vault_app_id, slope_change_box_name))

    # Opcode Budget
    # 103 flat budget + 285 per iteration
    required_opcode_budget = (103 + new_total_power_count * 285)
    # Increase budget app call consumes 14 budget
    increase_txn_count = math.ceil((required_opcode_budget - MAX_APP_PROGRAM_COST) / 686)

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[
                CREATE_CHECKPOINTS_APP_ARGUMENT,
            ],
            boxes=boxes[:MAX_APP_TOTAL_TXN_REFERENCES],
            note=app_call_note
        ),
        *[_prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, boxes=boxes[(i * MAX_APP_TOTAL_TXN_REFERENCES): (i * MAX_APP_TOTAL_TXN_REFERENCES) + MAX_APP_TOTAL_TXN_REFERENCES]) for i in range(1, increase_txn_count + 1)],
    ]

    # Min Balance
    if new_total_power_count > vault_app_global_state.free_total_power_space_count:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=TOTAL_POWER_BOX_COST
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_increase_lock_amount_transactions(
        vault_app_id: int,
        tiny_asset_id: int,
        sender: str,
        locked_amount: int,
        vault_app_global_state: VaultAppGlobalState,
        account_state: AccountState,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    if locked_amount < MIN_LOCK_AMOUNT_INCREMENT:
        raise InsufficientLockAmount()

    # Boxes
    account_state_box_name = get_account_state_box_name(address=sender)
    account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index)
    total_powers_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)
    next_total_powers_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index + 1)
    slope_change_box_name = get_slope_change_box_name(timestamp=account_state.lock_end_time)
    boxes = [
        (vault_app_id, account_state_box_name),
        (vault_app_id, account_power_box_name),
        (vault_app_id, total_powers_box_name),
        (vault_app_id, next_total_powers_box_name),
        (vault_app_id, slope_change_box_name),
    ]

    # contract will create weekly checkpoints automatically
    new_total_power_timestamps = get_new_total_power_timestamps(vault_app_global_state.last_total_power_timestamp, int(time.time()))
    new_total_power_count = len(new_total_power_timestamps)
    for timestamp in new_total_power_timestamps:
        if timestamp % WEEK == 0:
            slope_change_box_name = get_slope_change_box_name(timestamp=timestamp)
            boxes.append((vault_app_id, slope_change_box_name))

    # Min balance
    min_balance_increase = 0
    if new_total_power_count > vault_app_global_state.free_total_power_space_count:
        min_balance_increase += TOTAL_POWER_BOX_COST

    if not account_state.free_account_power_space_count:
        new_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index + 1)
        boxes.append((vault_app_id, new_account_power_box_name))
        min_balance_increase += ACCOUNT_POWER_BOX_COST

    txns = [
        transaction.AssetTransferTxn(
            index=tiny_asset_id,
            sender=sender,
            receiver=get_application_address(vault_app_id),
            amt=locked_amount,
            sp=suggested_params,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[
                INCREASE_LOCK_AMOUNT_APP_ARGUMENT,
            ],
            boxes=boxes,
            note=app_call_note
        ),
        _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id),
    ]

    if min_balance_increase:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=min_balance_increase,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_extend_lock_end_time_transactions(
        vault_app_id: int,
        sender: str,
        new_lock_end_time: int,
        vault_app_global_state: VaultAppGlobalState,
        account_state: AccountState,
        slope_change_at_new_lock_end_time: Optional[int],
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    if new_lock_end_time % WEEK:
        raise InvalidLockEndTime()

    # Boxes
    account_state_box_name = decode_address(sender)
    account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index)
    total_powers_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)
    next_total_powers_box_name = get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index + 1)
    current_account_slope_change_box_name = get_slope_change_box_name(timestamp=account_state.lock_end_time)
    new_account_slope_change_box_name = get_slope_change_box_name(timestamp=new_lock_end_time)
    boxes = [
        (vault_app_id, account_state_box_name),
        (vault_app_id, account_power_box_name),
        (vault_app_id, total_powers_box_name),
        (vault_app_id, next_total_powers_box_name),
        (vault_app_id, current_account_slope_change_box_name),
        (vault_app_id, new_account_slope_change_box_name),
    ]

    if not account_state.free_account_power_space_count:
        new_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index + 1)
        boxes.append((vault_app_id, new_account_power_box_name))

    # contract will create weekly checkpoints automatically
    new_total_power_timestamps = get_new_total_power_timestamps(vault_app_global_state.last_total_power_timestamp, int(time.time()))
    new_total_power_count = len(new_total_power_timestamps)
    for timestamp in new_total_power_timestamps:
        if timestamp % WEEK == 0:
            slope_change_box_name = get_slope_change_box_name(timestamp=timestamp)
            boxes.append((vault_app_id, slope_change_box_name))

    # Min Balance
    min_balance_increase = 0
    if slope_change_at_new_lock_end_time is None:
        min_balance_increase += SLOPE_CHANGE_BOX_COST

    if not account_state.free_account_power_space_count:
        min_balance_increase += ACCOUNT_POWER_BOX_COST

    if new_total_power_count > vault_app_global_state.free_total_power_space_count:
        min_balance_increase += TOTAL_POWER_BOX_COST

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[
                EXTEND_LOCK_END_TIME_APP_ARGUMENT,
                new_lock_end_time
            ],
            boxes=boxes[:MAX_APP_TOTAL_TXN_REFERENCES],
            note=app_call_note
        ),
        _prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, boxes=boxes[MAX_APP_TOTAL_TXN_REFERENCES:]),
    ]

    if min_balance_increase:
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=min_balance_increase,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_withdraw_transactions(
        vault_app_id: int,
        tiny_asset_id: int,
        sender: str,
        account_state: AccountState,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
):
    # Boxes
    account_state_box_name = decode_address(sender)
    account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index)
    next_account_power_box_name = get_account_power_box_name(address=sender, box_index=account_state.last_account_power_box_index + 1)
    boxes = [
        (vault_app_id, account_state_box_name),
        (vault_app_id, account_power_box_name),
        (vault_app_id, next_account_power_box_name),
    ]

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[WITHDRAW_APP_ARGUMENT],
            foreign_assets=[tiny_asset_id],
            boxes=boxes,
            note=app_call_note
        )
    ]
    txns[0].fee *= 2

    # Min Balance
    if not account_state.free_account_power_space_count:
        min_balance_increase = ACCOUNT_POWER_BOX_COST
        minimum_balance_payment = transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(vault_app_id),
            amt=min_balance_increase,
        )
        txns.insert(0, minimum_balance_payment)

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_tiny_power_of_transactions(
        vault_app_id: int,
        sender: str,
        user_address: str,
        suggested_params: SuggestedParams,
):
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TINY_POWER_OF_APP_ARGUMENT, decode_address(user_address)],
            boxes=[
                (vault_app_id, decode_address(user_address)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_tiny_power_of_at_transactions(
        vault_app_id: int,
        sender: str,
        user_address: str,
        user_account_powers: list[AccountPower],
        timestamp: int,
        suggested_params: SuggestedParams,
):
    account_power_index = get_power_index_at(user_account_powers, timestamp)
    if account_power_index is None:
        account_power_index = 0
        account_power_box_index = 0
    else:
        account_power_box_index = account_power_index // ACCOUNT_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TINY_POWER_OF_AT_APP_ARGUMENT, decode_address(user_address), timestamp, account_power_index],
            boxes=[
                (vault_app_id, decode_address(user_address)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_account_cumulative_power_delta_transactions(
    vault_app_id: int,
        sender: str,
        user_address: str,
        user_account_powers: list[AccountPower],
        timestamp_1: int,
        timestamp_2: int,
        suggested_params: SuggestedParams,
):
    account_power_index_1 = get_power_index_at(user_account_powers, timestamp_1)
    if account_power_index_1 is None:
        account_power_index_1 = 0
        account_power_box_index_1 = 0
    else:
        account_power_box_index_1 = account_power_index_1 // ACCOUNT_POWER_BOX_ARRAY_LEN

    account_power_index_2 = get_power_index_at(user_account_powers, timestamp_2)
    if account_power_index_2 is None:
        account_power_index_2 = 0
        account_power_box_index_2 = 0
    else:
        account_power_box_index_2 = account_power_index_2 // ACCOUNT_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_ACCOUNT_CUMULATIVE_POWER_DELTA_APP_PREFIX, decode_address(user_address), timestamp_1, timestamp_2, account_power_index_1, account_power_index_2],
            boxes=[
                (vault_app_id, decode_address(user_address)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index_1)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index_1 + 1)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index_2)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index_2 + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_total_tiny_power_transactions(
        vault_app_id: int,
        sender: str,
        vault_app_global_state: VaultAppGlobalState,
        suggested_params: SuggestedParams,
):
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TOTAL_TINY_POWER_APP_ARGUMENT],
            boxes=[
                (vault_app_id, get_total_power_box_name(box_index=vault_app_global_state.last_total_power_box_index)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_total_tiny_power_of_at_transactions(
        vault_app_id: int,
        sender: str,
        timestamp: int,
        total_powers: list[TotalPower],
        suggested_params: SuggestedParams,
):
    total_power_index = get_power_index_at(total_powers, timestamp)
    if total_power_index is None:
        total_power_index = 0
        total_power_box_index = 0
    else:
        total_power_box_index = total_power_index // TOTAL_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TOTAL_TINY_POWER_AT_APP_ARGUMENT, timestamp, total_power_index],
            boxes=[
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index)),
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_total_cumulative_power_at_transactions(
        vault_app_id: int,
        sender: str,
        timestamp: int,
        total_powers: list[TotalPower],
        suggested_params: SuggestedParams,
):
    total_power_index = get_power_index_at(total_powers, timestamp)
    if total_power_index is None:
        total_power_index = 0
        total_power_box_index = 0
    else:
        total_power_box_index = total_power_index // TOTAL_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TOTAL_CUMULATIVE_POWER_AT_APP_ARGUMENT, timestamp, total_power_index],
            boxes=[
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index)),
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_total_cumulative_power_delta_transactions(
        vault_app_id: int,
        sender: str,
        timestamp_1: int,
        timestamp_2: int,
        total_powers: list[TotalPower],
        suggested_params: SuggestedParams,
):
    total_power_index_1 = get_power_index_at(total_powers, timestamp_1)
    if total_power_index_1 is None:
        total_power_index_1 = 0
        total_power_box_index_1 = 0
    else:
        total_power_box_index_1 = total_power_index_1 // TOTAL_POWER_BOX_ARRAY_LEN
    
    total_power_index_2 = get_power_index_at(total_powers, timestamp_2)
    if total_power_index_2 is None:
        total_power_index_2 = 0
        total_power_box_index_2 = 0
    else:
        total_power_box_index_2 = total_power_index_2 // TOTAL_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_TOTAL_CUMULATIVE_POWER_DELTA_APP_PREFIX, timestamp_1, timestamp_2, total_power_index_1, total_power_index_2],
            boxes=[
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index_1)),
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index_1 + 1)),
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index_2)),
                (vault_app_id, get_total_power_box_name(box_index=total_power_box_index_2 + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_cumulative_power_of_at_transactions(
        vault_app_id: int,
        sender: str,
        user_address: str,
        user_account_powers: list[AccountPower],
        timestamp: int,
        suggested_params: SuggestedParams,
):
    account_power_index = get_power_index_at(user_account_powers, timestamp)
    if account_power_index is None:
        account_power_index = 0
        account_power_box_index = 0
    else:
        account_power_box_index = account_power_index // ACCOUNT_POWER_BOX_ARRAY_LEN

    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[GET_CUMULATIVE_POWER_OF_AT_APP_ARGUMENT, decode_address(user_address), timestamp, account_power_index],
            boxes=[
                (vault_app_id, decode_address(user_address)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index)),
                (vault_app_id, get_account_power_box_name(address=user_address, box_index=account_power_box_index + 1)),
            ]
        )
    ]
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_delete_account_power_boxes_transactions(
        vault_app_id: int,
        sender: str,
        account_state: AccountState,
        box_count: int,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:
    assert box_count <= 127

    box_index_start = account_state.deleted_power_count // ACCOUNT_POWER_BOX_ARRAY_LEN
    account_state_box_name = get_account_state_box_name(address=sender)

    account_power_boxes = list()
    for i in range(box_count):
        box_index = box_index_start + i
        box_name = get_account_power_box_name(address=sender, box_index=box_index)
        account_power_boxes.append((vault_app_id, box_name))

    boxes = [
        (vault_app_id, account_state_box_name),
        *account_power_boxes,
    ]
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[DELETE_ACCOUNT_POWER_BOXES_APP_ARGUMENT, box_count],
            boxes=boxes[:MAX_APP_TOTAL_TXN_REFERENCES],
            note=app_call_note,
        ),
    ]
    txns[0].fee *= 2

    remaining_boxes = boxes[MAX_APP_TOTAL_TXN_REFERENCES:]
    for boxes_chunk in [remaining_boxes[i:i + MAX_APP_TOTAL_TXN_REFERENCES] for i in range(0, len(remaining_boxes), MAX_APP_TOTAL_TXN_REFERENCES)]:
        txns.append(_prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, boxes=boxes_chunk))

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_delete_account_state_transactions(
        vault_app_id: int,
        sender: str,
        account_state: AccountState,
        suggested_params: SuggestedParams,
        app_call_note: Optional[str] = None,
) -> TransactionGroup:

    box_index = account_state.deleted_power_count // ACCOUNT_POWER_BOX_ARRAY_LEN
    account_state_box_name = get_account_state_box_name(address=sender)

    deleted_power_count = account_state.deleted_power_count

    account_power_boxes = list()
    while deleted_power_count < account_state.power_count:
        box_name = get_account_power_box_name(address=sender, box_index=box_index)
        account_power_boxes.append((vault_app_id, box_name))

        box_index += 1
        deleted_power_count += ACCOUNT_POWER_BOX_ARRAY_LEN

    boxes = [
        (vault_app_id, account_state_box_name),
        *account_power_boxes,
    ]
    txns = [
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=vault_app_id,
            app_args=[DELETE_ACCOUNT_STATE_APP_ARGUMENT],
            boxes=boxes[:MAX_APP_TOTAL_TXN_REFERENCES],
            note=app_call_note,
        ),
    ]
    txns[0].fee *= 2

    remaining_boxes = boxes[MAX_APP_TOTAL_TXN_REFERENCES:]
    for boxes_chunk in [remaining_boxes[i:i + MAX_APP_TOTAL_TXN_REFERENCES] for i in range(0, len(remaining_boxes), MAX_APP_TOTAL_TXN_REFERENCES)]:
        txns.append(_prepare_budget_increase_transaction(sender, sp=suggested_params, index=vault_app_id, boxes=boxes_chunk))

    assert len(txns) <= 16, "delete account powers first"
    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_get_box_transaction(
        vault_app_id: int,
        **kwargs
) -> TransactionGroup:
    return _prepare_get_box_transaction(app_id=vault_app_id, **kwargs)

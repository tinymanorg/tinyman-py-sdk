import json
from base64 import b64decode, b64encode
from datetime import datetime
from hashlib import sha256
from typing import List

from algosdk.constants import payment_txn, assettransfer_txn
from algosdk.encoding import is_valid_address
from algosdk.future.transaction import ApplicationClearStateTxn, ApplicationCreateTxn, ApplicationOptInTxn, OnComplete, PaymentTxn, StateSchema, ApplicationUpdateTxn, ApplicationNoOpTxn

from tinyman.utils import TransactionGroup, apply_delta, bytes_to_int_list, int_list_to_bytes, int_to_bytes, timestamp_to_date_str


def prepare_create_transaction(args, sender, suggested_params):
    from .contracts import staking_app_def
    txn = ApplicationCreateTxn(
        sender=sender,
        sp=suggested_params,
        on_complete=OnComplete.NoOpOC.real,
        approval_program=b64decode(staking_app_def['approval_program']['bytecode']),
        clear_program=b64decode(staking_app_def['clear_program']['bytecode']),
        global_schema=StateSchema(**staking_app_def['global_state_schema']),
        local_schema=StateSchema(**staking_app_def['local_state_schema']),
        app_args=args,
    )
    return TransactionGroup([txn])


def prepare_update_transaction(app_id: int, sender, suggested_params):
    from .contracts import staking_app_def
    txn = ApplicationUpdateTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        approval_program=b64decode(staking_app_def['approval_program']['bytecode']),
        clear_program=b64decode(staking_app_def['clear_program']['bytecode']),
    )
    return TransactionGroup([txn])


def prepare_commit_transaction(app_id: int, program_id: int, program_account: str, pool_asset_id: int, amount:int, reward_asset_id:int , sender, suggested_params):
    txn = ApplicationNoOpTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        app_args=['commit', int_to_bytes(amount), int_to_bytes(program_id)],
        foreign_assets=[pool_asset_id, reward_asset_id],
        accounts=[program_account],
        note=b'tinymanStaking/v1:b' + int_to_bytes(program_id) + int_to_bytes(pool_asset_id) + int_to_bytes(amount)
    )
    return TransactionGroup([txn])


def parse_commit_transaction(txn, app_id: int):
    if txn.get('application-transaction'):
        app_call = txn['application-transaction']
        if app_call['on-completion'] != 'noop':
            return
        if app_call['application-id'] != app_id:
            return
        if app_call['application-args'][0] == b64encode(b'commit').decode():
            result = {}
            try:
                result['pooler'] = txn['sender']
                result['program_address'] = app_call['accounts'][0]
                result['pool_asset_id'] = app_call['foreign-assets'][0]
                result['program_id'] = int.from_bytes(b64decode(app_call['application-args'][2]), 'big')
                result['amount'] = int.from_bytes(b64decode(app_call['application-args'][1]), 'big')
                result['balance'] = int.from_bytes(b64decode(txn['logs'][0])[8:], 'big')
                return result
            except Exception as e:
                return
    return


def parse_program_config_transaction(txn, app_id: int):
    if txn.get('application-transaction'):
        app_call = txn['application-transaction']
        if app_call['application-id'] != app_id:
            return
        if app_call['on-completion'] == 'clear':
            return ('clear', None)
        arg1 = b64decode(app_call['application-args'][0]).decode()
        local_delta = txn['local-state-delta'][0]['delta']
        return (arg1, local_delta)
    return


def parse_program_update_transaction(txn, app_id: int):
    if txn.get('application-transaction'):
        app_call = txn['application-transaction']
        if app_call['on-completion'] != 'noop':
            return
        if app_call['application-id'] != app_id:
            return
        if app_call['application-args'][0] == b64encode(b'update').decode():
            try:
                local_delta = txn['local-state-delta'][0]['delta']
                state = apply_delta({}, local_delta)
                result = parse_program_state(txn['sender'], state)
                return result
            except Exception as e:
                return
    return


def parse_program_state(address, state):
    result = {}
    result['address'] = address
    result['id'] = state[b'id']
    result['url'] = state[b'url']
    result['reward_asset_id'] = state[b'reward_asset_id']
    result['reward_period'] = state[b'reward_period']
    result['start_date'] = timestamp_to_date_str(state[b'start_time'])
    result['end_date'] = timestamp_to_date_str(state[b'end_time'])
    result['pools'] = []
    asset_ids = bytes_to_int_list(state[b'assets'])
    result['asset_ids'] = asset_ids
    mins = bytes_to_int_list(state[b'mins'])
    result['mins'] = mins
    empty_rewards_bytes = int_list_to_bytes([0] * 15)
    rewards = []
    for i in range(1, 8):
        r = bytes_to_int_list(state.get(f'r{i}'.encode(), empty_rewards_bytes))
        start = r[0]
        amounts = r[1:]
        if start:
            rewards.append({'start_date': timestamp_to_date_str(start), 'amounts': amounts})
    result['reward_amounts_dict'] = rewards
    for i in range(len(asset_ids)):
        if asset_ids[i] > 0:
            result['pools'].append({
                'asset_id': asset_ids[i],
                'min_amount': mins[i],
                'reward_amounts': {x['start_date']: x['amounts'][i] for x in rewards},
            })
    return result


def prepare_setup_transaction(app_id: int, url: str, reward_asset_id: int, reward_period: int, start_time: int, end_time: int, asset_ids: List[int], min_amounts: List[int], sender, suggested_params):
    assets = [0] * 14
    mins = [0] * 14
    for i in range(len(asset_ids)):
        assets[i] = asset_ids[i]
        mins[i] = min_amounts[i]
    txn = ApplicationOptInTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        # setup, url, reward_asset_id, reward_period, start_time, end_time, int[14]{asset_id_1, asset_id_2, ...}
        app_args=[
            'setup',
            url,
            int_to_bytes(reward_asset_id),
            int_to_bytes(reward_period),
            int_to_bytes(start_time),
            int_to_bytes(end_time),
            int_list_to_bytes(assets),
            int_list_to_bytes(mins),
        ],
        foreign_assets=[reward_asset_id],
    )
    return TransactionGroup([txn])


def prepare_clear_state_transaction(app_id, sender, suggested_params):
    clear_txn = ApplicationClearStateTxn(index=app_id, sender=sender, sp=suggested_params)
    return TransactionGroup([clear_txn])


def prepare_update_rewards_transaction(app_id: int, reward_amounts_dict: dict, sender, suggested_params):
    r = [
        [0] * 15,
        [0] * 15,
        [0] * 15,
        [0] * 15,
        [0] * 15,
    ]
    for i, start_time in enumerate(sorted(reward_amounts_dict.keys())):
        amounts = reward_amounts_dict[start_time]
        r[i][0] = start_time
        for j, x in enumerate(amounts):
            r[i][j+1] = x

    txn = ApplicationNoOpTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        # ("update_rewards", int[15]{rewards_first_valid_time, rewards_asset_1, rewards_asset_2, ...}, int[15]{rewards_first_valid_time, rewards_asset_1, rewards_asset_2, ...}, ...)
        app_args=[
            'update_rewards',
            int_list_to_bytes(r[0]),
            int_list_to_bytes(r[1]),
            int_list_to_bytes(r[2]),
            int_list_to_bytes(r[3]),
            int_list_to_bytes(r[4]),
        ],
    )
    return TransactionGroup([txn])


def prepare_payment_transaction(staker_address: str, reward_asset_id: int, amount: int, metadata: dict, sender, suggested_params):
    note = generate_note_from_metadata(metadata)
    # Compose a lease key from the distribution key (date, pool_address) and staker_address
    # This is to prevent accidently submitting multiple payments for the same staker for the same cycles
    # Note: the lease is only ensured unique between first_valid & last_valid
    lease_data = json.dumps([metadata['rewards']['distribution'], staker_address]).encode()
    lease = sha256(lease_data).digest()
    if reward_asset_id == 0:
        txn = PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=staker_address,
            amt=amount,
            note=note,
            lease=lease,
        )
        return txn
    else:
        raise NotImplemented()


def prepare_reward_metadata_for_payment(distribution_date: str, cycles_rewards: List[List], pool_address: int, pool_asset_id: int, pool_name: str):
    data = {
        "rewards": {
            "distribution": distribution_date + '_' + pool_address,
            "pool_address": pool_address,
            "pool_asset_id": pool_asset_id,
            "pool_name": pool_name,
            "rewards": [[str(cycle), str(amount)] for (cycle, amount) in cycles_rewards],
        },
    }
    return data


def generate_note_from_metadata(metadata):
    note = b'tinymanStaking/v1:j' + json.dumps(metadata, sort_keys=True).encode()
    return note


def get_note_prefix_for_distribution(distribution_date, pool_address):
    metadata = prepare_reward_metadata_for_payment(distribution_date, cycles_rewards=[], pool_address=pool_address, pool_asset_id=None, pool_name=None)
    note = generate_note_from_metadata(metadata)
    prefix = note.split(b', "pool_address"')[0]
    return prefix


def parse_reward_payment_transaction(txn):
    prefix = "tinymanStaking/v1:j"
    date_format = "%Y%m%d"

    if "note" not in txn:
        return

    if txn["tx-type"] == payment_txn:
        reward_asset_id = 0
        staker_address = txn["payment-transaction"]["receiver"]
        transfer_amount = txn["payment-transaction"]["amount"]
    elif txn["tx-type"] == assettransfer_txn:
        reward_asset_id = txn["asset-transfer-transaction"]["asset-id"]
        staker_address = txn["asset-transfer-transaction"]["receiver"]
        transfer_amount = txn["asset-transfer-transaction"]["amount"]
    else:
        return

    note = b64decode(txn['note']).decode()
    if not note.startswith(prefix):
        return

    data = json.loads(note.lstrip(prefix))
    if "rewards" not in data:
        return

    payment_data = data["rewards"]

    if not {"distribution", "pool_address", "pool_name", "pool_asset_id", "rewards"} <= set(payment_data):
        return

    if not isinstance(payment_data["rewards"], list):
        return

    if not payment_data["rewards"]:
        return

    try:
        distribution_date, pool_address = payment_data["distribution"].split("_")
        distribution_date = datetime.strptime(distribution_date, date_format).date()
    except ValueError:
        return

    if pool_address != payment_data["pool_address"]:
        return

    if not is_valid_address(pool_address):
        return

    try:
        pool_asset_id = int(payment_data["pool_asset_id"])
    except ValueError:
        return

    rewards = []
    try:
        for cycle, reward_amount in payment_data["rewards"]:
            rewards.append({
                "cycle": datetime.strptime(cycle, date_format).date(),
                "amount": int(reward_amount)
            })
    except ValueError:
        return

    total_reward = sum([reward["amount"] for reward in rewards])

    if total_reward < transfer_amount:
        return

    result = {
        "distribution_date": distribution_date,
        "program_address": txn["sender"],
        "staker_address": staker_address,
        "pool_address": pool_address,
        "pool_name": payment_data["pool_name"],
        "pool_asset_id": pool_asset_id,
        "reward_asset_id": reward_asset_id,
        "rewards": rewards,
    }
    return result



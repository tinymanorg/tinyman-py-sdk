from base64 import b64decode, b64encode
from algosdk.future.transaction import ApplicationCreateTxn, OnComplete, StateSchema, ApplicationUpdateTxn, ApplicationNoOpTxn
from tinyman.utils import TransactionGroup, int_to_bytes
from .contracts import staking_app_def


def prepare_create_transaction(sender, suggested_params):
    txn = ApplicationCreateTxn(
        sender=sender,
        sp=suggested_params,
        on_complete=OnComplete.NoOpOC.real,
        approval_program=b64decode(staking_app_def['approval_program']['bytecode']),
        clear_program=b64decode(staking_app_def['clear_program']['bytecode']),
        global_schema=StateSchema(**staking_app_def['global_state_schema']),
        local_schema=StateSchema(**staking_app_def['local_state_schema']),
    )
    return TransactionGroup([txn])


def prepare_update_transaction(app_id, sender, suggested_params):
    txn = ApplicationUpdateTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        approval_program=b64decode(staking_app_def['approval_program']['bytecode']),
        clear_program=b64decode(staking_app_def['clear_program']['bytecode']),
    )
    return TransactionGroup([txn])

def prepare_commit_transaction(app_id, program_id, program_account, pool_asset_id, amount, sender, suggested_params):
    txn = ApplicationNoOpTxn(
        index=app_id,
        sender=sender,
        sp=suggested_params,
        app_args=['commit', int_to_bytes(amount), int_to_bytes(program_id)],
        foreign_assets=[pool_asset_id],
        accounts=[program_account],
        note=b'tinymanStaking/v1:b' + int_to_bytes(program_id) + int_to_bytes(pool_asset_id) + int_to_bytes(amount)
    )
    return TransactionGroup([txn])


def parse_commit_transaction(txn, app_id):
    if txn.get('application-transaction'):
        app_call = txn['application-transaction']
        if app_call['application-id'] == app_id and app_call['application-args'][0] == b64encode('commit'):
            result = {}
            result['pooler'] = txn['sender']
            result['program_address'] = app_call['accounts'][0]
            result['pool_asset_id'] = app_call['foreign-assets'][0]
            result['program_id'] = int.from_bytes(b64decode(app_call['application-args'][2]), 'big')
            result['amount'] = int.from_bytes(b64decode(app_call['application-args'][1]), 'big')
            result['balance'] = int.from_bytes(b64decode(txn['logs'][0])[8:], 'big')
            return result
    return None

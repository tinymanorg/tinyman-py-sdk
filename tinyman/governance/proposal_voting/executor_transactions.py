from base64 import b32decode, b64decode
from hashlib import sha256

from algosdk import transaction
from algosdk.encoding import _correct_padding, decode_address
from algosdk.logic import get_application_address

from tinyman.compat import SuggestedParams
from tinyman.governance.proposal_voting.constants import (
    ASSET_OPTIN_APP_ARGUMENT,
    SEND_APP_ARGUMENT,
    SEND_HASH_PREFIX,
    SET_FEE_COLLECTOR_APP_ARGUMENT,
    SET_FEE_COLLECTOR_HASH_PREFIX,
    SET_FEE_FOR_POOL_APP_ARGUMENT,
    SET_FEE_FOR_POOL_HASH_PREFIX,
    SET_FEE_MANAGER_APP_ARGUMENT,
    SET_FEE_MANAGER_HASH_PREFIX,
    SET_FEE_SETTER_APP_ARGUMENT,
    SET_FEE_SETTER_HASH_PREFIX,
    VALIDATE_GROUP_APP_ARGUMENT,
    VALIDATE_GROUP_HASH_PREFIX,
    VALIDATE_TRANSACTION_APP_ARGUMENT,
    VALIDATE_TRANSACTION_HASH_PREFIX,
)
from tinyman.governance.proposal_voting.storage import get_proposal_box_name
from tinyman.utils import TransactionGroup, int_to_bytes


def get_arbitrary_transaction_execution_hash(txn: transaction.Transaction):
    execution_hash = b32decode(_correct_padding(txn.get_txid()))
    execution_hash = VALIDATE_TRANSACTION_HASH_PREFIX + execution_hash
    return execution_hash


def get_arbitrary_transaction_group_execution_hash(txn_group: TransactionGroup):
    execution_hash = b64decode(txn_group.id)
    execution_hash = VALIDATE_GROUP_HASH_PREFIX + execution_hash
    return execution_hash


def prepare_validate_transaction_transactions(
    arbitrary_executor_app_id: int,
    proposal_voting_app_id: int,
    proposal_id: str,
    transaction_to_validate: transaction.Transaction,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=arbitrary_executor_app_id,
        app_args=[VALIDATE_TRANSACTION_APP_ARGUMENT, proposal_id],
        foreign_apps=[proposal_voting_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )
    txn_group = TransactionGroup([executor_transaction, transaction_to_validate])
    return txn_group


def prepare_validate_group_transactions(
    arbitrary_executor_app_id: int,
    proposal_voting_app_id: int,
    proposal_id: str,
    group_to_validate: TransactionGroup,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=arbitrary_executor_app_id,
        app_args=[VALIDATE_GROUP_APP_ARGUMENT, proposal_id],
        foreign_apps=[proposal_voting_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )
    txn_group = TransactionGroup([executor_transaction] + group_to_validate.transactions)
    return txn_group


def get_set_fee_setter_transactions_execution_hash(new_fee_setter: str):
    execution_hash = bytes("set_fee_setter", "utf-8") + decode_address(new_fee_setter)
    execution_hash = sha256(execution_hash).digest()
    execution_hash = SET_FEE_SETTER_HASH_PREFIX + execution_hash

    return execution_hash


def prepare_set_fee_setter_transactions(
    fee_management_executor_app_id: int,
    proposal_voting_app_id: int,
    amm_app_id: str,
    proposal_id: str,
    new_fee_setter: str,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=fee_management_executor_app_id,
        app_args=[SET_FEE_SETTER_APP_ARGUMENT, proposal_id, decode_address(new_fee_setter)],
        accounts=[new_fee_setter],
        foreign_apps=[proposal_voting_app_id, amm_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )

    txn_group = TransactionGroup([executor_transaction])
    return txn_group


def get_set_fee_manager_transactions_execution_hash(new_fee_manager: str):
    execution_hash = bytes("set_fee_manager", "utf-8") + decode_address(new_fee_manager)
    execution_hash = sha256(execution_hash).digest()
    execution_hash = SET_FEE_MANAGER_HASH_PREFIX + execution_hash

    return execution_hash


def prepare_set_fee_manager_transactions(
    fee_management_executor_app_id: int,
    proposal_voting_app_id: int,
    amm_app_id: str,
    proposal_id: str,
    new_fee_manager: str,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=fee_management_executor_app_id,
        app_args=[SET_FEE_MANAGER_APP_ARGUMENT, proposal_id, decode_address(new_fee_manager)],
        accounts=[new_fee_manager],
        foreign_apps=[proposal_voting_app_id, amm_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )

    txn_group = TransactionGroup([executor_transaction])
    return txn_group


def get_set_fee_collector_transactions_execution_hash(new_fee_collector: str):
    execution_hash = bytes("set_fee_collector", "utf-8") + decode_address(new_fee_collector)
    execution_hash = sha256(execution_hash).digest()
    execution_hash = SET_FEE_COLLECTOR_HASH_PREFIX + execution_hash

    return execution_hash


def prepare_set_fee_collector_transactions(
    fee_management_executor_app_id: int,
    proposal_voting_app_id: int,
    amm_app_id: str,
    proposal_id: str,
    new_fee_collector: str,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=fee_management_executor_app_id,
        app_args=[SET_FEE_COLLECTOR_APP_ARGUMENT, proposal_id, decode_address(new_fee_collector)],
        accounts=[new_fee_collector],
        foreign_apps=[proposal_voting_app_id, amm_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )

    txn_group = TransactionGroup([executor_transaction])
    return txn_group


def get_set_fee_for_pool_transactions_execution_hash(
    pool_address: str, pool_total_fee_share: int, pool_protocol_fee_ratio: int
):
    execution_hash = (
        bytes("set_fee_for_pool", "utf-8")
        + decode_address(pool_address)
        + int_to_bytes(pool_total_fee_share)
        + int_to_bytes(pool_protocol_fee_ratio)
    )
    execution_hash = sha256(execution_hash).digest()
    execution_hash = SET_FEE_FOR_POOL_HASH_PREFIX + execution_hash

    return execution_hash


def prepare_set_fee_for_pool_transactions(
    fee_management_executor_app_id: int,
    proposal_voting_app_id: int,
    amm_app_id: str,
    proposal_id: str,
    pool_address: str,
    pool_total_fee_share: int,
    pool_protocol_fee_ratio: int,
    sender: str,
    suggested_params: SuggestedParams,
):
    executor_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=fee_management_executor_app_id,
        app_args=[
            SET_FEE_FOR_POOL_APP_ARGUMENT,
            proposal_id,
            decode_address(pool_address),
            int_to_bytes(pool_total_fee_share),
            int_to_bytes(pool_protocol_fee_ratio),
        ],
        accounts=[pool_address],
        foreign_apps=[proposal_voting_app_id, amm_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
    )

    txn_group = TransactionGroup([executor_transaction])
    return txn_group


def get_send_transactions_execution_hash(treasury_account: str, receiver: str, amount: int, asset_id: int):
    execution_hash = (
        bytes("send", "utf-8")
        + decode_address(treasury_account)
        + decode_address(receiver)
        + int_to_bytes(amount)
        + int_to_bytes(asset_id)
    )
    execution_hash = sha256(execution_hash).digest()
    execution_hash = SEND_HASH_PREFIX + execution_hash

    return execution_hash


def prepare_send_transactions(
    treasury_management_executor_app_id: int,
    proposal_voting_app_id: int,
    proposal_id: str,
    treasury_account: str,
    receiver: str,
    asset_id: int,
    amount: int,
    sender: str,
    suggested_params: SuggestedParams,
):
    send_transaction = transaction.ApplicationNoOpTxn(
        sender=sender,
        sp=suggested_params,
        index=treasury_management_executor_app_id,
        app_args=[
            SEND_APP_ARGUMENT,
            proposal_id,
            decode_address(treasury_account),
            decode_address(receiver),
            amount,
            asset_id,
        ],
        foreign_apps=[proposal_voting_app_id],
        boxes=[(proposal_voting_app_id, get_proposal_box_name(proposal_id))],
        accounts=[treasury_account, receiver],
    )
    txn_group = TransactionGroup([send_transaction])
    return txn_group


def prepare_asset_optin_transactions(
    sender: str,
    suggested_params: SuggestedParams,
    app_id: int,
    asset_id: int,
):
    txns = [
        transaction.PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=get_application_address(app_id),
            amt=100000,
        ),
        transaction.ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=app_id,
            app_args=[ASSET_OPTIN_APP_ARGUMENT, int_to_bytes(asset_id)],
            foreign_assets=[asset_id],
        ),
    ]

    # 1 inner transaction
    txns[1].fee *= 2

    txn_group = TransactionGroup(txns)
    return txn_group

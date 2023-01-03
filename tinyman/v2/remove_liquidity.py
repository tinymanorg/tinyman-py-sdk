from typing import Optional

from algosdk.future.transaction import (
    ApplicationNoOpTxn,
    AssetTransferTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from .constants import REMOVE_LIQUIDITY_APP_ARGUMENT
from .contracts import get_pool_logicsig


def prepare_remove_liquidity_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_token_asset_id: int,
    min_asset_1_amount: int,
    min_asset_2_amount: int,
    pool_token_asset_amount: int,
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            index=pool_token_asset_id,
            amt=pool_token_asset_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                REMOVE_LIQUIDITY_APP_ARGUMENT,
                min_asset_1_amount,
                min_asset_2_amount,
            ],
            foreign_assets=[asset_1_id, asset_2_id],
            accounts=[pool_address],
            note=app_call_note,
        ),
    ]

    # App call contains 2 inner transactions
    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 3
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_single_asset_remove_liquidity_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_token_asset_id: int,
    output_asset_id: int,
    min_output_asset_amount: int,
    pool_token_asset_amount: int,
    sender: str,
    suggested_params: SuggestedParams,
    app_call_note: Optional[str] = None,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    if output_asset_id == asset_1_id:
        min_asset_1_amount = min_output_asset_amount
        min_asset_2_amount = 0
    elif output_asset_id == asset_2_id:
        min_asset_1_amount = 0
        min_asset_2_amount = min_output_asset_amount
    else:
        assert False

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            index=pool_token_asset_id,
            amt=pool_token_asset_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                REMOVE_LIQUIDITY_APP_ARGUMENT,
                min_asset_1_amount,
                min_asset_2_amount,
            ],
            foreign_assets=[output_asset_id],
            accounts=[pool_address],
            note=app_call_note,
        ),
    ]

    # App call contains 2 inner transactions
    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 3
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group

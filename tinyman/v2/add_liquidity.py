from typing import Optional

from algosdk.future.transaction import (
    ApplicationNoOpTxn,
    PaymentTxn,
    AssetTransferTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from .constants import (
    ADD_LIQUIDITY_APP_ARGUMENT,
    ADD_LIQUIDITY_FLEXIBLE_MODE_APP_ARGUMENT,
    ADD_LIQUIDITY_SINGLE_MODE_APP_ARGUMENT,
    ADD_INITIAL_LIQUIDITY_APP_ARGUMENT,
)
from .contracts import get_pool_logicsig


def prepare_flexible_add_liquidity_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_token_asset_id: int,
    asset_1_amount: int,
    asset_2_amount: int,
    min_pool_token_asset_amount: int,
    sender: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_1_amount,
            index=asset_1_id,
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_2_amount,
            index=asset_2_id,
        )
        if asset_2_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_2_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                ADD_LIQUIDITY_APP_ARGUMENT,
                ADD_LIQUIDITY_FLEXIBLE_MODE_APP_ARGUMENT,
                min_pool_token_asset_amount,
            ],
            foreign_assets=[pool_token_asset_id],
            accounts=[pool_address],
        ),
    ]

    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 3
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_single_asset_add_liquidity_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_token_asset_id: int,
    min_pool_token_asset_amount: int,
    sender: str,
    suggested_params: SuggestedParams,
    asset_1_amount: Optional[int] = None,
    asset_2_amount: Optional[int] = None,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    assert bool(asset_1_amount) != bool(
        asset_2_amount
    ), "If you want to add asset 1 and asset 2 at the same time, please use flexible add liquidity."

    if asset_1_amount:
        asset_in_id = asset_1_id
        asset_in_amount = asset_1_amount

    elif asset_2_amount:
        asset_in_id = asset_2_id
        asset_in_amount = asset_2_amount

    else:
        assert False

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_in_amount,
            index=asset_in_id,
        )
        if asset_in_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_in_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                ADD_LIQUIDITY_APP_ARGUMENT,
                ADD_LIQUIDITY_SINGLE_MODE_APP_ARGUMENT,
                min_pool_token_asset_amount,
            ],
            foreign_assets=[pool_token_asset_id],
            accounts=[pool_address],
        ),
    ]

    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 3
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group


def prepare_initial_add_liquidity_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    pool_token_asset_id: int,
    asset_1_amount: int,
    asset_2_amount: int,
    sender: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_1_amount,
            index=asset_1_id,
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_2_amount,
            index=asset_2_id,
        )
        if asset_2_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=asset_2_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[ADD_INITIAL_LIQUIDITY_APP_ARGUMENT],
            foreign_assets=[pool_token_asset_id],
            accounts=[pool_address],
        ),
    ]

    min_fee = suggested_params.min_fee
    app_call_fee = min_fee * 2
    txns[-1].fee = app_call_fee

    txn_group = TransactionGroup(txns)
    return txn_group

from algosdk.encoding import decode_address
from algosdk.logic import get_application_address

from tinyman.compat import ApplicationNoOpTxn, AssetTransferTxn, PaymentTxn, SuggestedParams
from tinyman.utils import TransactionGroup


def prepare_add_liquidity_transaction_group(
    sender: str,
    suggested_params: SuggestedParams,
    wrapper_app_id: int,
    tinyman_amm_app_id: int,
    lending_app_1_id: int,
    lending_app_2_id: int,
    lending_manager_app_id: int,
    tinyman_pool_address: str,
    asset_1_id: int,
    asset_2_id: int,
    f_asset_1_id: int,
    f_asset_2_id: int,
    liquidity_token_id: int,
    asset_1_amount: int,
    asset_2_amount: int,
):
    wrapper_application_address = get_application_address(wrapper_app_id)

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=wrapper_application_address,
            amt=asset_1_amount,
            index=asset_1_id,
        ),
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=wrapper_application_address,
            amt=asset_2_amount,
            index=asset_2_id,
        ) if asset_2_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=wrapper_application_address,
            amt=asset_2_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=wrapper_app_id,
            app_args=[
                b"add_liquidity",
                decode_address(tinyman_pool_address),
                lending_app_1_id,
                lending_app_2_id,
            ],
            accounts=[tinyman_pool_address],
            foreign_apps=[lending_app_1_id, lending_app_2_id, lending_manager_app_id],
            foreign_assets=[asset_1_id, asset_2_id, f_asset_1_id, f_asset_2_id],
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=wrapper_app_id,
            foreign_apps=[tinyman_amm_app_id],
            foreign_assets=[liquidity_token_id],
            accounts=[tinyman_pool_address],
            app_args=[
                b"noop",
            ],
        ),
    ]

    min_fee = suggested_params.min_fee
    txns[2].fee = min_fee * 16

    return TransactionGroup(txns)


def prepare_remove_liquidity_transaction_group(
    sender: int,
    suggested_params: SuggestedParams,
    wrapper_app_id: int,
    tinyman_amm_app_id: int,
    lending_app_1_id: int,
    lending_app_2_id: int,
    lending_manager_app_id: int,
    tinyman_pool_address: str,
    asset_1_id: int,
    asset_2_id: int,
    f_asset_1_id: int,
    f_asset_2_id: int,
    liquidity_token_id: int,
    liquidity_token_amount: int
):
    wrapper_application_address = get_application_address(wrapper_app_id)
    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=wrapper_application_address,
            index=liquidity_token_id,
            amt=liquidity_token_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=wrapper_app_id,
            app_args=[
                b"remove_liquidity",
                decode_address(tinyman_pool_address),
                lending_app_1_id,
                lending_app_2_id,
            ],
            foreign_apps=[lending_app_1_id, lending_app_2_id, lending_manager_app_id],
            foreign_assets=[asset_1_id, asset_2_id, f_asset_1_id, f_asset_2_id],
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=wrapper_app_id,
            app_args=[
                b"noop",
            ],
            foreign_apps=[tinyman_amm_app_id],
            foreign_assets=[liquidity_token_id, f_asset_1_id, f_asset_2_id],
            accounts=[tinyman_pool_address],
        ),
    ]

    min_fee = suggested_params.min_fee
    txns[1].fee = min_fee * 15

    return TransactionGroup(txns)


def prepare_asset_optin_transaction_group(
    sender: str,
    suggested_params: SuggestedParams,
    wrapper_app_id: int,
    assets_to_optin: list[int],
):
    wrapper_application_address = get_application_address(wrapper_app_id)
    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=wrapper_application_address,
            amt=100_000 * len(assets_to_optin),
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=wrapper_app_id,
            app_args=[
                b"asset_optin",
                *assets_to_optin
            ],
            foreign_assets=assets_to_optin,
        ),
    ]

    min_fee = suggested_params.min_fee
    txns[1].fee = min_fee * (len(assets_to_optin) + 1)

    return TransactionGroup(txns)

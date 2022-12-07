from algosdk.future.transaction import AssetTransferTxn, ApplicationNoOpTxn, SuggestedParams, PaymentTxn
from tinyman.utils import TransactionGroup
from tinyman.v2.constants import FIXED_INPUT_APP_ARGUMENT, FIXED_OUTPUT_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig

SWAP_ROUTER_APP_ID = 0
SWAP_ROUTER_ADDRESS = ""


def prepare_swap_router_transactions(
    router_app_id: int,
    amm_app_id: int,
    input_asset_id: int,
    intermediary_asset_id: int,
    output_asset_id: int,
    asset_in_amount: int,
    asset_out_amount: int,
    swap_type: [str, bytes],
    sender: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    # TODO: WIP
    pool_1_logicsig = get_pool_logicsig(amm_app_id, input_asset_id, intermediary_asset_id)
    pool_1_address = pool_1_logicsig.address()

    pool_2_logicsig = get_pool_logicsig(amm_app_id, intermediary_asset_id, output_asset_id)
    pool_2_address = pool_2_logicsig.address()

    txns = [
        AssetTransferTxn(
            sender=sender,
            sp=suggested_params,
            receiver=SWAP_ROUTER_ADDRESS,
            index=input_asset_id,
            amt=asset_in_amount,
        )
        if input_asset_id != 0
        else PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=SWAP_ROUTER_ADDRESS,
            amt=asset_in_amount,
        ),
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=router_app_id,
            app_args=["swap", swap_type, asset_out_amount],
            accounts=[pool_1_address, pool_2_address],
            foreign_apps=[amm_app_id],
            foreign_assets=[input_asset_id, intermediary_asset_id, output_asset_id],
        )
    ]

    if isinstance(swap_type, bytes):
        pass
    elif isinstance(swap_type, str):
        swap_type = swap_type.encode()
    else:
        raise NotImplementedError()

    min_fee = suggested_params.min_fee
    if swap_type == FIXED_INPUT_APP_ARGUMENT:
        app_call_fee = min_fee * 8
    elif swap_type == FIXED_OUTPUT_APP_ARGUMENT:
        app_call_fee = min_fee * 9
    else:
        raise NotImplementedError()

    txns[-1].fee = app_call_fee
    txn_group = TransactionGroup(txns)
    return txn_group

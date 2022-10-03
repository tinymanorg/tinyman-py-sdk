from algosdk.future.transaction import (
    ApplicationOptInTxn,
    PaymentTxn,
    SuggestedParams,
)
from algosdk.logic import get_application_address

from tinyman.utils import TransactionGroup
from .constants import BOOTSTRAP_APP_ARGUMENT
from .contracts import get_pool_logicsig


def prepare_bootstrap_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    sender: str,
    app_call_fee: int,
    required_algo: int,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()
    assert asset_1_id > asset_2_id

    txns = list()

    # Fund pool account to cover minimum balance and fee requirements
    if required_algo:
        txns.append(
            PaymentTxn(
                sender=sender,
                sp=suggested_params,
                receiver=pool_address,
                amt=int(required_algo),
            )
        )

    # Bootstrap (Opt-in) App Call
    bootstrap_app_call = ApplicationOptInTxn(
        sender=pool_address,
        sp=suggested_params,
        index=validator_app_id,
        app_args=[BOOTSTRAP_APP_ARGUMENT],
        foreign_assets=[asset_1_id, asset_2_id],
        rekey_to=get_application_address(validator_app_id),
    )
    bootstrap_app_call.fee = app_call_fee
    txns.append(bootstrap_app_call)

    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicisg(pool_logicsig)
    return txn_group

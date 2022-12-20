from algosdk.future.transaction import (
    Transaction,
    ApplicationNoOpTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from .constants import (
    FLASH_SWAP_APP_ARGUMENT,
    VERIFY_FLASH_SWAP_APP_ARGUMENT,
)
from .contracts import get_pool_logicsig


def prepare_flash_swap_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    asset_1_loan_amount: int,
    asset_2_loan_amount: int,
    transactions: "list[Transaction]",
    sender: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    assert asset_1_loan_amount or asset_2_loan_amount

    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()
    min_fee = suggested_params.min_fee

    if asset_1_loan_amount and asset_2_loan_amount:
        inner_transaction_count = 2
    else:
        inner_transaction_count = 1

    index_diff = len(transactions) + 1
    txns = [
        # Flash Swap
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                FLASH_SWAP_APP_ARGUMENT,
                index_diff,
                asset_1_loan_amount,
                asset_2_loan_amount,
            ],
            foreign_assets=[asset_1_id, asset_2_id],
            accounts=[pool_address],
        )
    ]
    # This app call contains inner transactions
    txns[0].fee = min_fee * (inner_transaction_count + 1)

    if transactions:
        txns.extend(transactions)

    # Verify Flash Swap
    txns.append(
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[VERIFY_FLASH_SWAP_APP_ARGUMENT, index_diff],
            foreign_assets=[asset_1_id, asset_2_id],
            accounts=[pool_address],
        )
    )

    txn_group = TransactionGroup(txns)
    return txn_group

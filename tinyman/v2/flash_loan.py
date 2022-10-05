from algosdk.future.transaction import (
    Transaction,
    ApplicationNoOpTxn,
    PaymentTxn,
    AssetTransferTxn,
    SuggestedParams,
)

from tinyman.utils import TransactionGroup
from .constants import (
    FLASH_LOAN_APP_ARGUMENT,
    VERIFY_FLASH_LOAN_APP_ARGUMENT,
)
from .contracts import get_pool_logicsig


def prepare_flash_loan_transactions(
    validator_app_id: int,
    asset_1_id: int,
    asset_2_id: int,
    asset_1_loan_amount: int,
    asset_2_loan_amount: int,
    asset_1_payment_amount: int,
    asset_2_payment_amount: int,
    transactions: list[Transaction],
    sender: str,
    suggested_params: SuggestedParams,
) -> TransactionGroup:
    assert asset_1_loan_amount or asset_2_loan_amount

    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()
    min_fee = suggested_params.min_fee

    if asset_1_loan_amount and asset_2_loan_amount:
        payment_count = inner_transaction_count = 2
    else:
        payment_count = inner_transaction_count = 1

    index_diff = len(transactions) + payment_count + 1
    txns = [
        # Flash Loan
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[
                FLASH_LOAN_APP_ARGUMENT,
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

    if asset_1_loan_amount:
        txns.append(
            AssetTransferTxn(
                sender=sender,
                sp=suggested_params,
                receiver=pool_address,
                index=asset_1_id,
                amt=asset_1_payment_amount,
            )
        )

    if asset_2_loan_amount:
        if asset_2_id:
            txns.append(
                AssetTransferTxn(
                    sender=sender,
                    sp=suggested_params,
                    receiver=pool_address,
                    index=asset_2_id,
                    amt=asset_2_payment_amount,
                )
            )
        else:
            txns.append(
                PaymentTxn(
                    sender=sender,
                    sp=suggested_params,
                    receiver=pool_address,
                    amt=asset_2_payment_amount,
                )
            )

    # Verify Flash Loan
    txns.append(
        ApplicationNoOpTxn(
            sender=sender,
            sp=suggested_params,
            index=validator_app_id,
            app_args=[VERIFY_FLASH_LOAN_APP_ARGUMENT, index_diff],
            foreign_assets=[],
            accounts=[pool_address],
        )
    )

    txn_group = TransactionGroup(txns)
    return txn_group

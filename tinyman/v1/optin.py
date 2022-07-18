from algosdk.future.transaction import ApplicationOptInTxn, AssetOptInTxn
from tinyman.utils import TransactionGroup


def prepare_app_optin_transactions(validator_app_id, sender, suggested_params):
    txn = ApplicationOptInTxn(
        sender=sender,
        sp=suggested_params,
        index=validator_app_id,
    )
    txn_group = TransactionGroup([txn])
    return txn_group


def prepare_asset_optin_transactions(asset_id, sender, suggested_params):
    txn = AssetOptInTxn(
        sender=sender,
        sp=suggested_params,
        index=asset_id,
    )
    txn_group = TransactionGroup([txn])
    return txn_group

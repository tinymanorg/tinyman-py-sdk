import base64
from os import name
import algosdk
from algosdk.future.transaction import ApplicationOptInTxn, PaymentTxn, AssetCreateTxn, AssetOptInTxn, assign_group_id, LogicSigTransaction
from algosdk.v2client.algod import AlgodClient

from .contracts import validator_app_def, get_pool_logicsig
from tinyman.utils import int_to_bytes


def get_bootstrap_with_algo_transactions(client: AlgodClient, sender, asset1_id, validator_app_id):
    suggested_params = client.suggested_params()
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, 0)
    pool_address = pool_logicsig.address()

    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=860000,
        ),
        ApplicationOptInTxn(
            sender=pool_address,
            sp=suggested_params,
            index=validator_app_id,
            app_args=['bootstrap', int_to_bytes(asset1_id), int_to_bytes(0)],
            foreign_assets=[asset1_id],
        ),
        AssetCreateTxn(
            sender=pool_address,
            sp=suggested_params,
            total=0xFFFFFFFFFFFFFFFF,
            decimals=6,
            unit_name='TM1POOL',
            asset_name='Tinyman Pool USDC-ALGO',
            url='https://tinyman.org',
            default_frozen=False,
        ),
        AssetOptInTxn(
            sender=pool_address,
            sp=suggested_params,
            index=asset1_id,
        )
    ]
    txns = assign_group_id(txns)

    signed_transactions = []
    for txn in txns:
        if txn.sender == pool_address:
            signed_transactions.append(LogicSigTransaction(txn, pool_logicsig))
        else:
            signed_transactions.append(None)
    return txns, signed_transactions
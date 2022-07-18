from algosdk.future.transaction import ApplicationOptInTxn, AssetCreateTxn, AssetOptInTxn, PaymentTxn
from tinyman.utils import TransactionGroup, int_to_bytes

from .contracts import get_pool_logicsig


def prepare_bootstrap_transactions(validator_app_id, asset1_id, asset2_id, asset1_unit_name, asset2_unit_name, sender, suggested_params):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()

    assert(asset1_id > asset2_id)

    if asset2_id == 0:
        asset2_unit_name = 'ALGO'

    txns = [
        PaymentTxn(
            sender=sender,
            sp=suggested_params,
            receiver=pool_address,
            amt=961000 if asset2_id > 0 else 860000,
            note='fee',
        ),
        ApplicationOptInTxn(
            sender=pool_address,
            sp=suggested_params,
            index=validator_app_id,
            app_args=['bootstrap', int_to_bytes(asset1_id), int_to_bytes(asset2_id)],
            foreign_assets=[asset1_id] if asset2_id == 0 else [asset1_id, asset2_id],
        ),
        AssetCreateTxn(
            sender=pool_address,
            sp=suggested_params,
            total=0xFFFFFFFFFFFFFFFF,
            decimals=6,
            unit_name='TMPOOL11',
            asset_name=f'TinymanPool1.1 {asset1_unit_name}-{asset2_unit_name}',
            url='https://tinyman.org',
            default_frozen=False,
        ),
        AssetOptInTxn(
            sender=pool_address,
            sp=suggested_params,
            index=asset1_id,
        ),
    ]
    if asset2_id > 0:
        txns += [
            AssetOptInTxn(
                sender=pool_address,
                sp=suggested_params,
                index=asset2_id,
            )
        ]
    txn_group = TransactionGroup(txns)
    txn_group.sign_with_logicisg(pool_logicsig)
    return txn_group

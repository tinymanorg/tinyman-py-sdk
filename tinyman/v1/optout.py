from typing import Optional

from tinyman.compat import ApplicationClearStateTxn
from algosdk.v2client.algod import AlgodClient


def get_optout_transactions(
    client: AlgodClient,
    sender,
    validator_app_id,
    app_call_note: Optional[str] = None,
):
    suggested_params = client.suggested_params()

    txn = ApplicationClearStateTxn(
        sender=sender,
        sp=suggested_params,
        index=validator_app_id,
        note=app_call_note,
    )

    return [txn], [None]

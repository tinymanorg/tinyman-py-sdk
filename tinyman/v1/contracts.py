import json
import importlib.resources
from algosdk.future.transaction import LogicSig
import tinyman.v1
from tinyman.utils import get_program

_contracts = json.loads(importlib.resources.read_text(tinyman.v1, 'contracts.json'))

pool_logicsig_def = _contracts['contracts']['pool_logicsig']['logic']

validator_app_def = _contracts['contracts']['validator_app']


def get_pool_logicsig(validator_app_id, asset1_id, asset2_id):
    program_bytes = get_program(pool_logicsig_def, variables=dict(
        validator_app_id=validator_app_id,
        asset_id_1=asset1_id,
        asset_id_2=asset2_id,
    ))
    return LogicSig(program=program_bytes)

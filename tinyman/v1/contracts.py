import json
import importlib.resources
from algosdk.future.transaction import LogicSig
import tinyman.v1
from tinyman.utils import get_program
from .constants import ASC_FILE_V1_0, ASC_FILE_V1_1

def get_pool_logicsig(validator_app_id, asset1_id, asset2_id):
    if int(validator_app_id) == 350338509:
        use_asc = ASC_FILE_V1_0
    elif int(validator_app_id) == 552635992:
        use_asc = ASC_FILE_V1_1
    contracts = json.loads(importlib.resources.read_text(tinyman.v1, use_asc))
    pool_logicsig_def = contracts['contracts']['pool_logicsig']['logic']
    validator_app_def = contracts['contracts']['validator_app']

    assets = [asset1_id, asset2_id]
    asset_id_1 = max(assets)
    asset_id_2 = min(assets)
    program_bytes = get_program(pool_logicsig_def, variables=dict(
        validator_app_id=validator_app_id,
        asset_id_1=asset_id_1,
        asset_id_2=asset_id_2,
    ))
    return LogicSig(program=program_bytes)

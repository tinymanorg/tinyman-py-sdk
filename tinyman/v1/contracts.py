import json
import importlib.resources
from algosdk.future.transaction import LogicSig
import tinyman.v1
from tinyman.utils import get_program

_contracts = json.loads(importlib.resources.read_text(tinyman.v1, "asc.json"))

pool_logicsig_def = _contracts["contracts"]["pool_logicsig"]["logic"]

validator_app_def = _contracts["contracts"]["validator_app"]


def get_pool_logicsig(validator_app_id, asset1_id, asset2_id):
    assets = [asset1_id, asset2_id]
    asset_id_1 = max(assets)
    asset_id_2 = min(assets)
    program_bytes = get_program(
        pool_logicsig_def,
        variables=dict(
            validator_app_id=validator_app_id,
            asset_id_1=asset_id_1,
            asset_id_2=asset_id_2,
        ),
    )
    return LogicSig(program=program_bytes)

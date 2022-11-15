import json
import importlib.resources
from base64 import b64decode

from algosdk.future.transaction import LogicSigAccount

import tinyman.v1


_contracts = json.loads(importlib.resources.read_text(tinyman.v2, "asc.json"))

pool_logicsig_def = _contracts["contracts"]["pool_logicsig"]["logic"]

# TODO: Update "asc.json"
# validator_app_def = _contracts["contracts"]["validator_app"]


def get_pool_logicsig(
    validator_app_id: int, asset_1_id: int, asset_2_id: int
) -> LogicSigAccount:
    assets = [asset_1_id, asset_2_id]
    asset_1_id = max(assets)
    asset_2_id = min(assets)

    program = bytearray(b64decode(pool_logicsig_def["bytecode"]))
    program[3:11] = validator_app_id.to_bytes(8, "big")
    program[11:19] = asset_1_id.to_bytes(8, "big")
    program[19:27] = asset_2_id.to_bytes(8, "big")
    return LogicSigAccount(program)

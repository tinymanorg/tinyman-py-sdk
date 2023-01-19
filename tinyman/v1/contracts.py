import sys
import json
import importlib.resources
from tinyman.compat import LogicSigAccount
import tinyman.v1
from base64 import b64decode
from tinyman.utils import encode_value

if sys.version_info >= (3, 9):
    _contracts = json.loads(
        importlib.resources.files(tinyman.v1).joinpath("asc.json").read_text()
    )
else:
    _contracts = json.loads(importlib.resources.read_text(tinyman.v1, "asc.json"))

pool_logicsig_def = _contracts["contracts"]["pool_logicsig"]["logic"]

validator_app_def = _contracts["contracts"]["validator_app"]


def get_program(definition, variables=None):
    """
    Return a byte array to be used in LogicSig.
    """
    template = definition["bytecode"]
    template_bytes = list(b64decode(template))

    offset = 0
    for v in sorted(definition["variables"], key=lambda v: v["index"]):
        name = v["name"].split("TMPL_")[-1].lower()
        value = variables[name]
        start = v["index"] - offset
        end = start + v["length"]
        value_encoded = encode_value(value, v["type"])
        value_encoded_len = len(value_encoded)
        diff = v["length"] - value_encoded_len
        offset += diff
        template_bytes[start:end] = list(value_encoded)

    return bytes(template_bytes)


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
    return LogicSigAccount(program=program_bytes)

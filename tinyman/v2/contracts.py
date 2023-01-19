from base64 import b64decode

from tinyman.compat import LogicSigAccount

from tinyman.v2.constants import POOL_LOGICSIG_TEMPLATE


def get_pool_logicsig(
    validator_app_id: int, asset_a_id: int, asset_b_id: int
) -> LogicSigAccount:
    assets = [asset_a_id, asset_b_id]
    asset_1_id = max(assets)
    asset_2_id = min(assets)

    program = bytearray(b64decode(POOL_LOGICSIG_TEMPLATE))
    program[3:11] = validator_app_id.to_bytes(8, "big")
    program[11:19] = asset_1_id.to_bytes(8, "big")
    program[19:27] = asset_2_id.to_bytes(8, "big")
    return LogicSigAccount(program)

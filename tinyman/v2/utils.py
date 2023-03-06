import sys
import importlib.resources
import json
from base64 import b64decode

import tinyman.v2
from tinyman.swap_router.constants import TESTNET_SWAP_ROUTER_APP_ID_V1, MAINNET_SWAP_ROUTER_APP_ID_V1
from tinyman.tealishmap import TealishMap
from tinyman.utils import bytes_to_int
from tinyman.v2.constants import TESTNET_VALIDATOR_APP_ID, MAINNET_VALIDATOR_APP_ID

if sys.version_info >= (3, 9):
    amm_tealishmap = TealishMap(
        json.loads(
            importlib.resources.files(tinyman.v2)
            .joinpath("amm_approval.map.json")
            .read_text()
        )
    )
    swap_router_tealishmap = TealishMap(
        json.loads(
            importlib.resources.files(tinyman.v2)
            .joinpath("swap_router_approval.map.json")
            .read_text()
        )
    )


else:
    amm_tealishmap = TealishMap(
        json.loads(importlib.resources.read_text(tinyman.v2, "amm_approval.map.json"))
    )
    swap_router_tealishmap = TealishMap(
        json.loads(importlib.resources.read_text(tinyman.v2, "swap_router_approval.map.json"))
    )


def decode_logs(logs: "list") -> dict:
    decoded_logs = dict()
    for log in logs:
        if type(log) == str:
            log = b64decode(log.encode())
        if b"%i" in log:
            i = log.index(b"%i")
            s = log[0:i].decode()
            value = int.from_bytes(log[i + 2 :], "big")
            decoded_logs[s] = value
        else:
            raise NotImplementedError()
    return decoded_logs


def get_state_from_account_info(account_info, app_id):
    try:
        app = [a for a in account_info["apps-local-state"] if a["id"] == app_id][0]
    except IndexError:
        return {}
    try:
        app_state = {}
        for x in app["key-value"]:
            key = b64decode(x["key"]).decode()
            if x["value"]["type"] == 1:
                value = bytes_to_int(b64decode(x["value"].get("bytes", "")))
            else:
                value = x["value"].get("uint", 0)
            app_state[key] = value
    except KeyError:
        return {}
    return app_state


def get_tealishmap(app_id):
    maps = {
        TESTNET_VALIDATOR_APP_ID: amm_tealishmap,
        MAINNET_VALIDATOR_APP_ID: amm_tealishmap,
        TESTNET_SWAP_ROUTER_APP_ID_V1: swap_router_tealishmap,
        MAINNET_SWAP_ROUTER_APP_ID_V1: swap_router_tealishmap
    }
    return maps.get(app_id)


def lookup_error(pc, error_message, tealishmap):
    tealish_line_no = tealishmap.get_tealish_line_for_pc(int(pc))
    if "assert failed" in error_message or "err opcode executed" in error_message:
        custom_error_message = tealishmap.get_error_for_pc(int(pc))
        if custom_error_message:
            error_message = custom_error_message

    error_message = f"{error_message} @ line {tealish_line_no}"
    return error_message

from base64 import b64decode
from typing import Union, Optional
from algosdk.encoding import decode_address
from algosdk.constants import ZERO_ADDRESS
from algosdk.logic import get_application_address


def parse_swap_router_event_log(log: Union[bytes, str]) -> Optional[dict]:
    # Signature is "swap(uint64,uint64,uint64,uint64)"
    swap_event_selector = b"\x81b\xda\x9e"

    if isinstance(log, str):
        # Indexer returns logs as b64 encoded.
        log = b64decode(log)

    if log[:4] == swap_event_selector and len(log) >= 36:
        return dict(
            input_asset_id=int.from_bytes(log[4:12], "big"),
            output_asset_id=int.from_bytes(log[12:20], "big"),
            input_amount=int.from_bytes(log[20:28], "big"),
            output_amount=int.from_bytes(log[28:36], "big"),
        )

    return None


# TODO: Move these later.
def int_to_bytes(num, length=8):
    return num.to_bytes(length, "big")


def int_array(elements, size, default=0):
    array = [default] * size
    for i in range(len(elements)):
        array[i] = elements[i]
    bytes = b"".join(map(int_to_bytes, array))
    return bytes


def bytes_array(elements, size, default=b""):
    array = [default] * size
    for i in range(len(elements)):
        array[i] = elements[i]
    bytes = b"".join(array)
    return bytes


def encode_router_args(route, pools):
    route_arg = int_array(route, size=8, default=0)
    pools_arg = bytes_array([decode_address(a) for a in pools], size=8, default=decode_address(ZERO_ADDRESS))
    return route_arg, pools_arg


def group_references(route, pools, amm_app_id, talgo_asset_id, talgo_app_id, talgo_app_accounts):
    talgo_app_address = get_application_address(talgo_app_id)
    is_talgo_app_used = False
    swaps = len(pools)
    pairs = []
    for i in range(swaps):
        pool = pools[i]

        if pool == talgo_app_address:
            is_talgo_app_used = True
            continue

        assets = route[i], route[i + 1]
        pairs.append((pool, assets))

    # Group account and asset references for every 2 step in route.
    grouped_references = []
    for i in range(0, 8, 2):
        refs = {"accounts": [], "assets": [], "apps": [amm_app_id]}

        for pool, assets in pairs[i: i + 2]:
            refs["accounts"].append(pool)
            refs["assets"] += assets

        refs["assets"] = list(set(refs["assets"]))

        if not refs["accounts"]:
            break

        grouped_references.append(refs)

    if is_talgo_app_used:
        grouped_references.append({
            "apps": [talgo_app_id],
            "accounts": talgo_app_accounts[1:5],
            "assets": [talgo_asset_id],
        })

    return grouped_references

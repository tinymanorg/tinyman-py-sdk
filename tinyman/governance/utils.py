import json
import pickle
from base64 import b64decode
from hashlib import sha256
from typing import Optional

from algosdk.error import AlgodHTTPError
from multiformats import CID

from tinyman.constants import MINIMUM_BALANCE_REQUIREMENT_PER_BOX, MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE


def get_raw_box_value(
        algod,
        app_id: int,
        box_name: bytes,
        cache: bool = False
) -> Optional[bytes]:
    cache_filename = f"tinyman-governance-box-cache-{app_id}"

    cache_data = {}
    if cache:
        try:
            with open(cache_filename, 'rb') as cache_file:
                cache_data = pickle.load(cache_file)
        except FileNotFoundError:
            pass

    if box_name in cache_data:
        raw_box = cache_data[box_name]
    else:
        try:
            response = algod.application_box_by_name(app_id, box_name)
        except AlgodHTTPError as e:
            if str(e) != 'box not found':
                raise e
            return None

        value = response["value"]
        raw_box = b64decode(value)

        if cache:
            cache_data[box_name] = raw_box
            with open(cache_filename, 'wb') as cache_file:
                pickle.dump(cache_data, cache_file)
    return raw_box


def get_all_box_names(algod, app_id: int) -> list[bytes]:
    response = algod.application_boxes(app_id, limit=0)
    box_names = [b64decode(box["name"]) for box in response["boxes"]]
    return box_names


def box_exists(algod, app_id: int, box_name: bytes) -> bool:
    return get_raw_box_value(algod, app_id, box_name) is not None


def parse_global_state_from_application_info(application_info: dict) -> dict:
    raw_global_state = application_info["params"]["global-state"]

    global_state = {}
    for pair in raw_global_state:
        key = b64decode(pair["key"]).decode()
        if pair["value"]["type"] == 1:
            value = b64decode(pair["value"].get("bytes", ""))
        else:
            value = pair["value"].get("uint", 0)
        global_state[key] = value

    return global_state


def get_global_state(algod, app_id: int) -> dict:
    application_info = algod.application_info(app_id)
    global_state = parse_global_state_from_application_info(application_info)
    return global_state


def check_nth_bit_from_left(value_bytes: bytes, n: int) -> int:
    # ensure n is within the range of the bytes
    if n >= len(value_bytes) * 8:
        raise ValueError(f"n should be less than {len(value_bytes) * 8}")

    # convert bytes to int
    num = int.from_bytes(value_bytes, 'big')

    # calculate which bit to check from the left
    bit_to_check = (len(value_bytes) * 8 - 1) - n

    # create a number with nth bit set
    nth_bit = 1 << bit_to_check

    # if the nth bit is set in the given number, return 1. Otherwise, return 0
    if num & nth_bit:
        return 1
    else:
        return 0


def get_required_minimum_balance_of_box(box_name: bytes, box_size: int):
    return MINIMUM_BALANCE_REQUIREMENT_PER_BOX + MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE * (len(box_name) + box_size)


def serialize_metadata(metadata: dict) -> str:
    serialized_metadata = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return serialized_metadata


def generate_cid_from_serialized_metadata(serialized_metadata: str) -> str:
    digest = sha256(serialized_metadata.encode('utf-8')).digest()
    cid = CID("base32", 1, "raw", ("sha2-256", digest))
    return str(cid)


def generate_cid_from_proposal_metadata(metadata: dict) -> str:
    serialized_metadata = serialize_metadata(metadata)
    return generate_cid_from_serialized_metadata(serialized_metadata)

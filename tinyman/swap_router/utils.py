from base64 import b64decode
from typing import Union, Optional


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

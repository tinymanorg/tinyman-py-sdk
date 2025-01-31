import json
import re
import warnings
from base64 import b64decode, b64encode
from datetime import datetime
from json import JSONDecodeError
from typing import Optional

from algosdk.error import AlgodHTTPError
from tinyman.compat import (
    LogicSigTransaction,
    assign_group_id,
    wait_for_confirmation,
)
from .errors import AlgodError, LogicError, OverspendError

from tinyman.v1.constants import (
    MAINNET_VALIDATOR_APP_ID_V1_1,
    TESTNET_VALIDATOR_APP_ID_V1_1,
)
from tinyman.v2.constants import (
    MAINNET_VALIDATOR_APP_ID_V2,
    TESTNET_VALIDATOR_APP_ID_V2,
)

warnings.simplefilter("always", DeprecationWarning)


def encode_value(value, type):
    if type == "int":
        return encode_varint(value)
    raise Exception("Unsupported value type %s!" % type)


def encode_varint(number):
    buf = b""
    while True:
        towrite = number & 0x7F
        number >>= 7
        if number:
            buf += bytes([towrite | 0x80])
        else:
            buf += bytes([towrite])
            break
    return buf


def sign_and_submit_transactions(
    client, transactions, signed_transactions, sender, sender_sk
):
    for i, txn in enumerate(transactions):
        if txn.sender == sender:
            signed_transactions[i] = txn.sign(sender_sk)

    txid = client.send_transactions(signed_transactions)
    txn_info = wait_for_confirmation(client, txid)
    txn_info["txid"] = txid
    return txn_info


def int_to_bytes(num, length=8):
    return num.to_bytes(length, "big")


def int_list_to_bytes(nums):
    return b"".join([int_to_bytes(x) for x in nums])


def bytes_to_int(b):
    if isinstance(b, str):
        b = b64decode(b)
    return int.from_bytes(b, "big")


def bytes_to_int_list(b):
    n = len(b) // 8
    return [bytes_to_int(b[(i * 8) : ((i + 1) * 8)]) for i in range(n)]


def get_state_int(state, key):
    if isinstance(key, str):
        key = b64encode(key.encode())
    return state.get(key.decode(), {"uint": 0})["uint"]


def get_state_bytes(state, key):
    if isinstance(key, str):
        key = b64encode(key.encode())
    return state.get(key.decode(), {"bytes": ""})["bytes"]


def lpad(string: bytes, n: int) -> bytes:
    assert (n > 0)

    return b"\x00" * (n - len(string)) + string


def apply_delta(state, delta):
    state = dict(state)
    for d in delta:
        key = b64decode(d["key"])
        if d["value"]["action"] == 1:
            state[key] = b64decode(d["value"].get("bytes", ""))
        elif d["value"]["action"] == 2:
            state[key] = d["value"].get("uint", 0)
        elif d["value"]["action"] == 3:
            state.pop(key)
        else:
            raise Exception(d["value"]["action"])
    return state


def timestamp_to_date_str(t):
    d = datetime.fromtimestamp(t).date()
    return d.strftime("%Y-%m-%d")


def calculate_price_impact(
    input_supply, output_supply, swap_input_amount, swap_output_amount
):
    swap_price = swap_output_amount / swap_input_amount
    pool_price = output_supply / input_supply
    price_impact = round(1 - (swap_price / pool_price), 5)
    return price_impact


def get_version(tinyman_app_id: int) -> str:
    if tinyman_app_id in [MAINNET_VALIDATOR_APP_ID_V2, TESTNET_VALIDATOR_APP_ID_V2]:
        return "v2"
    elif tinyman_app_id in [
        MAINNET_VALIDATOR_APP_ID_V1_1,
        TESTNET_VALIDATOR_APP_ID_V1_1,
    ]:
        return "v1"

    raise NotImplementedError()


def generate_app_call_note(
    version: str, client_name: Optional[str] = None, extra_data: Optional[dict] = None, dapp_name: str = "tinyman",
) -> str:
    # https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0002.md
    # <dapp-name>:<data-format><data>
    note_template = "{dapp_name}/{dapp_version}:{data_format}{data}"

    client_name = client_name or "tinyman-py-sdk"
    assert version in ["v1", "v2"]

    data = extra_data or dict()
    data.update(
        {
            "origin": client_name,
        }
    )

    # spaces are removed from separators, default is (', ', ': ')
    serialized_data = json.dumps(data, separators=(",", ":"), sort_keys=True)

    note = note_template.format(
        dapp_name=dapp_name, dapp_version=version, data_format="j", data=serialized_data
    )
    return note


def parse_app_call_note(
    note: [str, bytes], raise_exception: bool = False
) -> Optional[dict]:
    if isinstance(note, str):
        try:
            note = b64decode(note)
        except Exception:
            pass

    if isinstance(note, bytes):
        try:
            note = note.decode()
        except Exception as e:
            if raise_exception:
                raise e
            return None

    pattern = r"tinyman/(?P<version>v[1-2]):j(?P<raw_data>.*)$"
    match = re.match(pattern, note)

    if not match:
        return None

    try:
        data = json.loads(match.group("raw_data"))
    except JSONDecodeError as e:
        if raise_exception:
            raise e
        return None

    # Result
    result = {"version": match.group("version"), "data": data}
    return result


class TransactionGroup:
    def __init__(self, transactions):
        # Clear previously assigned group ids
        for txn in transactions:
            txn.group = None

        transactions = assign_group_id(transactions)
        self.transactions = transactions
        self.signed_transactions = [None for _ in self.transactions]

    @property
    def id(self):
        try:
            byte_group_id = self.transactions[0].group
        except IndexError:
            return

        group_id = b64encode(byte_group_id).decode("utf-8")
        return group_id

    def sign_with_logicisg(self, logicsig):
        """
        Deprecated because of the typo. Use sign_with_logicsig instead.
        """
        warnings.warn(
            "tinyman.utils.TransactionGroup.sign_with_logicisg is deprecated. Use tinyman.utils.TransactionGroup.sign_with_logicsig instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.sign_with_logicsig(logicsig)

    def sign_with_logicsig(self, logicsig, address=None):
        if address is None:
            address = logicsig.address()

        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = LogicSigTransaction(txn, logicsig)

    def sign_with_private_key(self, address, private_key):
        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = txn.sign(private_key)

    def submit(self, algod, wait=False):
        try:
            txid = algod.send_transactions(self.signed_transactions)
        except AlgodHTTPError as e:
            raise Exception(e) from None
        if wait:
            txn_info = wait_for_confirmation(algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def __add__(self, other):
        transactions = self.transactions + other.transactions
        return TransactionGroup(transactions)


def parse_error(exception):
    error_message = str(exception)
    pattern = r"Remember: transaction ([A-Z0-9]+):"
    try:
        txn_id = re.findall(pattern, error_message)[0]
    except IndexError:
        return AlgodError(error_message)

    if "logic eval error" in error_message:
        pattern = r"error: (.+?). Details: pc=(\d+)"
        error, pc = re.findall(pattern, error_message)[0]
        return LogicError(error, txn_id=txn_id, pc=pc)

    if "overspend" in error_message:
        pattern = r"overspend \(account (.+?),.+tried to spend {(\d+)}\)"
        address, amount = re.findall(pattern, error_message)[0]
        return OverspendError(txn_id=txn_id, address=address, amount=amount)

    return AlgodError(error_message)


def find_app_id_from_txn_id(transaction_group, txn_id):
    app_id = None
    for txn in transaction_group.transactions:
        if txn.get_txid() == txn_id:
            app_id = txn.index
            break
    return app_id


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

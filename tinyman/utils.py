from base64 import b64decode, b64encode
import warnings
from datetime import datetime
from algosdk.future.transaction import (
    LogicSigTransaction,
    assign_group_id,
    wait_for_confirmation as wait_for_confirmation_algosdk,
)
from algosdk.error import AlgodHTTPError

warnings.simplefilter("always", DeprecationWarning)


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
    txinfo = wait_for_confirmation_algosdk(client, txid)
    txinfo["txid"] = txid
    return txinfo


def wait_for_confirmation(client, txid):
    """
    Deprecated.
    Use algosdk if you are importing wait_for_confirmation individually.
    """
    warnings.warn(
        "tinyman.utils.wait_for_confirmation is deprecated. Use algosdk.future.transaction.wait_for_confirmation instead if you are importing individually.",
        DeprecationWarning,
        stacklevel=2,
    )
    txinfo = wait_for_confirmation_algosdk(client, txid)
    txinfo["txid"] = txid
    return txinfo


def int_to_bytes(num):
    return num.to_bytes(8, "big")


def int_list_to_bytes(nums):
    return b"".join([int_to_bytes(x) for x in nums])


def bytes_to_int(b):
    return int.from_bytes(b, "big")


def bytes_to_int_list(b):
    n = len(b) // 8
    return [bytes_to_int(b[(i * 8) : ((i + 1) * 8)]) for i in range(n)]


def get_state_int(state, key):
    if type(key) == str:
        key = b64encode(key.encode())
    return state.get(key.decode(), {"uint": 0})["uint"]


def get_state_bytes(state, key):
    if type(key) == str:
        key = b64encode(key.encode())
    return state.get(key.decode(), {"bytes": ""})["bytes"]


def get_state_from_account_info(account_info, app_id):
    try:
        app = [a for a in account_info["apps-local-state"] if a["id"] == app_id][0]
    except IndexError:
        return {}
    try:
        app_state = {}
        for x in app["key-value"]:
            key = b64decode(x["key"])
            if x["value"]["type"] == 1:
                value = b64decode(x["value"].get("bytes", ""))
            else:
                value = x["value"].get("uint", 0)
            app_state[key] = value
    except KeyError:
        return {}
    return app_state


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


class TransactionGroup:
    def __init__(self, transactions):
        transactions = assign_group_id(transactions)
        self.transactions = transactions
        self.signed_transactions = [None for _ in self.transactions]

    def sign(self, user):
        user.sign_transaction_group(self)

    def sign_with_logicisg(self, logicsig):
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
            raise Exception(str(e))
        if wait:
            txinfo = wait_for_confirmation_algosdk(algod, txid)
            txinfo["txid"] = txid
            return txinfo
        return {"txid": txid}

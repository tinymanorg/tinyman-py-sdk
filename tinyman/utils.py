from base64 import b64decode, b64encode
from datetime import datetime
from algosdk.future.transaction import (
    LogicSigTransaction,
    assign_group_id,
    wait_for_confirmation,
)
from algosdk.error import AlgodHTTPError


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


def int_to_bytes(num):
    return num.to_bytes(8, "big")


def int_list_to_bytes(nums):
    return b"".join([int_to_bytes(x) for x in nums])


def bytes_to_int(b):
    if type(b) == str:
        b = b64decode(b)
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
    price_impact = abs(round((swap_price / pool_price) - 1, 5))
    return price_impact


class TransactionGroup:
    def __init__(self, transactions):
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
            txn_info = wait_for_confirmation(algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def __add__(self, other):
        transactions = self.transactions + other.transactions
        return TransactionGroup(transactions)

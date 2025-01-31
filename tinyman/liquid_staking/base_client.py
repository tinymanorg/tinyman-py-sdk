import time
from base64 import b64decode, b64encode

from algosdk import transaction
from algosdk.logic import get_application_address

# TODO: move struct to parent.
from tinyman.liquid_staking.struct import get_struct, get_box_costs
from tinyman.utils import get_global_state, TransactionGroup


class BaseClient():
    def __init__(self, algod, app_id, user_address, user_sk) -> None:
        self.algod = algod
        self.app_id = app_id
        self.application_address = get_application_address(self.app_id)
        self.user_address = user_address
        self.keys = {}
        self.add_key(user_address, user_sk)
        self.current_timestamp = None
        self.simulate = False

    def get_suggested_params(self):
        return self.algod.suggested_params()

    def get_current_timestamp(self):
        return self.current_timestamp or time.time()

    def _submit(self, transactions, additional_fees=0):
        transactions = self.flatten_transactions(transactions)
        fee = transactions[0].fee
        n = 0
        for txn in transactions:
            if txn.fee == fee:
                txn.fee = 0
                n += 1
        transactions[0].fee = (n + additional_fees) * fee
        txn_group = TransactionGroup(transactions)
        for address, key in self.keys.items():
            if isinstance(key, transaction.LogicSigAccount):
                txn_group.sign_with_logicsig(key, address=address)
            else:
                txn_group.sign_with_private_key(address, key)
        if self.simulate:
            txn_info = self.algod.simulate_raw_transactions(txn_group.signed_transactions)
        else:
            txn_info = txn_group.submit(self.algod, wait=True)
        return txn_info

    def flatten_transactions(self, txns):
        result = []
        if isinstance(txns, transaction.Transaction):
            result = [txns]
        elif isinstance(txns, list):
            for txn in txns:
                result += self.flatten_transactions(txn)
        return result

    def calculate_min_balance(self, accounts=0, assets=0, boxes=None):
        cost = 0
        cost += accounts * 100_000
        cost += assets * 100_000
        cost += get_box_costs(boxes or {})
        return cost

    def add_key(self, address, key):
        self.keys[address] = key

    def get_global(self, key, default=None, app_id=None):
        app_id = app_id or self.app_id
        global_state = {s["key"]: s["value"] for s in self.algod.application_info(app_id)["params"]["global-state"]}
        key = b64encode(key).decode()
        if key in global_state:
            value = global_state[key]
            if value["type"] == 2:
                return value["uint"]
            else:
                return b64decode(value["bytes"])
        else:
            return default

    def get_global_state(self, app_id=None):
        app_id = app_id or self.app_id

        return get_global_state(self.algod, app_id)

    def get_box(self, box_name, struct_name, app_id=None):
        app_id = app_id or self.app_id
        box_value = b64decode(self.algod.application_box_by_name(app_id, box_name)["value"])
        struct_class = get_struct(struct_name)
        struct = struct_class(box_value)
        return struct

    def box_exists(self, box_name, app_id=None):
        app_id = app_id or self.app_id
        try:
            self.algod.application_box_by_name(app_id, box_name)
            return True
        except Exception:
            return False

    def get_reward_slot(self, staking_asset_id, reward_asset_id):
        asset_box = self.get_asset_box(staking_asset_id)
        for i in range(8):
            if asset_box.reward_slots[i].asset_id == reward_asset_id:
                return i

    def is_opted_in(self, address, asset_id):
        try:
            self.algod.account_asset_info(address, asset_id)
            return True
        except Exception:
            return False

    def get_optin_if_needed_txn(self, sender, asset_id):
        if not self.is_opted_in(sender, asset_id):
            txn = transaction.AssetOptInTxn(
                sender=sender,
                sp=self.get_suggested_params(),
                index=asset_id,
            )
            return txn

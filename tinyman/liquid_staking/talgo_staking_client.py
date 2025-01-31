from datetime import datetime, timezone

from algosdk import transaction
from algosdk.encoding import decode_address
from algosdk.logic import get_application_address

from .base_client import BaseClient
from .constants import *
from .struct import get_struct


UserState = get_struct("UserState")


class TAlgoStakingClient(BaseClient):
    def __init__(self, algod, staking_app_id, vault_app_id, tiny_asset_id, talgo_asset_id, stalgo_asset_id, user_address, user_sk) -> None:
        self.algod = algod
        self.app_id = staking_app_id
        self.application_address = get_application_address(self.app_id)
        self.vault_app_id = vault_app_id
        self.tiny_asset_id = tiny_asset_id
        self.talgo_asset_id = talgo_asset_id
        self.stalgo_asset_id = stalgo_asset_id
        self.user_address = user_address
        self.keys = {}
        self.add_key(user_address, user_sk)
        self.current_timestamp = None
        self.simulate = False

    def set_reward_rate(self, total_reward_amount: int, end_timestamp: int):
        sp = self.get_suggested_params()

        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_reward_rate", total_reward_amount, end_timestamp],
                foreign_assets=[self.tiny_asset_id]
            )
        ]

        return self._submit(transactions)

    def propose_manager(self, new_manager_address):
        sp = self.get_suggested_params()

        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["propose_manager", decode_address(new_manager_address)],
            )
        ]

        return self._submit(transactions)

    def accept_manager(self):
        sp = self.get_suggested_params()

        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["accept_manager"],
            )
        ]

        return self._submit(transactions)

    def set_tiny_power_threshold(self, threshold: int):
        sp = self.get_suggested_params()

        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_tiny_power_threshold", threshold],
            )
        ]

        return self._submit(transactions)

    def get_apply_rate_change_txn(self):
        sp = self.get_suggested_params()

        txn = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["apply_rate_change"],
            )
        ]

        return txn

    def get_apply_rate_change_txn_if_needed(self):
        now = datetime.now(tz=timezone.utc).timestamp()
        current_rate_end_timestamp = self.get_global(CURRENT_REWARD_RATE_PER_TIME_END_TIMESTAMP_KEY)

        if current_rate_end_timestamp <= now:
            return self.get_apply_rate_change_txn()

    def apply_rate_change(self):
        transactions = [self.get_apply_rate_change_txn()]

        return self._submit(transactions)

    def update_state(self):
        sp = self.get_suggested_params()

        transactions = [
            self.get_apply_rate_change_txn_if_needed(),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["update_state"],
            )
        ]

        return self._submit(transactions)

    def get_user_state_box_name(self, account_address: str):
        return decode_address(account_address)

    def increase_stake(self, amount: int):
        sp = self.get_suggested_params()

        user_state_box_name = self.get_user_state_box_name(self.user_address)
        new_boxes = {}
        if not self.box_exists(user_state_box_name):
            new_boxes[user_state_box_name] = UserState

        transactions = [
            self.get_apply_rate_change_txn_if_needed(),
            transaction.PaymentTxn(
                sender=self.user_address,
                sp=sp,
                receiver=self.application_address,
                amt=self.calculate_min_balance(boxes=new_boxes)
            ) if new_boxes else None,
            self.get_optin_if_needed_txn(self.user_address, self.stalgo_asset_id),
            transaction.AssetTransferTxn(
                index=self.talgo_asset_id,
                sender=self.user_address,
                receiver=self.application_address,
                sp=sp,
                amt=amount
            ),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["increase_stake", amount],
                foreign_apps=[self.vault_app_id],
                foreign_assets=[self.stalgo_asset_id],
                boxes=[
                    (0, user_state_box_name),
                    (self.vault_app_id, user_state_box_name),
                ],
            )
        ]

        return self._submit(transactions, additional_fees=2)

    def decrease_stake(self, amount: int):
        sp = self.get_suggested_params()
        user_state_box_name = self.get_user_state_box_name(self.user_address)

        transactions = [
            self.get_apply_rate_change_txn_if_needed(),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["decrease_stake", amount],
                boxes=[
                    (0, user_state_box_name),
                ],
                foreign_assets=[self.talgo_asset_id, self.stalgo_asset_id],
            )
        ]

        return self._submit(transactions, additional_fees=2)

    def claim_rewards(self):
        sp = self.get_suggested_params()
        user_state_box_name = self.get_user_state_box_name(self.user_address)

        transactions = [
            self.get_apply_rate_change_txn_if_needed(),
            self.get_optin_if_needed_txn(self.user_address, self.tiny_asset_id),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["claim_rewards"],
                foreign_apps=[self.vault_app_id],
                foreign_assets=[self.tiny_asset_id],
                boxes=[
                    (0, user_state_box_name),
                    (self.vault_app_id, user_state_box_name),
                ],
            )
        ]

        return self._submit(transactions, additional_fees=3)

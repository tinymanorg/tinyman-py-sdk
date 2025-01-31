from algosdk import transaction
from algosdk.encoding import decode_address, encode_address
from .base_client import BaseClient


class TAlgoClient(BaseClient):

    def init(self):
        sp = self.get_suggested_params()
        transactions = [
            transaction.PaymentTxn(
                sender=self.user_address,
                receiver=self.application_address,
                sp=sp,
                amt=600_000,
            ),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["init"],
                accounts=[],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=13)

    def sync(self):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["sync"],
                accounts=[
                    encode_address(self.get_global(b"account_1")),
                    encode_address(self.get_global(b"account_2")),
                    encode_address(self.get_global(b"account_3")),
                    encode_address(self.get_global(b"account_4")),
                ],
                foreign_assets=[
                    self.get_global(b"talgo_asset_id"),
                ]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def mint(self, amount):
        sp = self.get_suggested_params()
        transactions = [
            self.get_optin_if_needed_txn(self.user_address, self.get_global(b"talgo_asset_id")),
            transaction.PaymentTxn(
                sender=self.user_address,
                receiver=self.application_address,
                sp=sp,
                amt=amount,
            ),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["mint", amount],
                accounts=[
                    encode_address(self.get_global(b"account_1")),
                    encode_address(self.get_global(b"account_2")),
                    encode_address(self.get_global(b"account_3")),
                    encode_address(self.get_global(b"account_4")),
                ],
                foreign_assets=[
                    self.get_global(b"talgo_asset_id"),
                ]
            ),
        ]
        return self._submit(transactions, additional_fees=4)

    def burn(self, amount):
        sp = self.get_suggested_params()
        transactions = [
            transaction.AssetTransferTxn(
                sender=self.user_address,
                receiver=self.application_address,
                sp=sp,
                amt=amount,
                index=self.get_global(b"talgo_asset_id")
            ),
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["burn", amount],
                accounts=[
                    encode_address(self.get_global(b"account_1")),
                    encode_address(self.get_global(b"account_2")),
                    encode_address(self.get_global(b"account_3")),
                    encode_address(self.get_global(b"account_4")),
                ],
                foreign_assets=[
                ]
            ),
        ]
        return self._submit(transactions, additional_fees=1)

    def get_state(self):
        state = self.get_globals()
        state[b"account_0"] = encode_address(state[b"account_0"])
        state[b"account_1"] = encode_address(state[b"account_1"])
        state[b"account_2"] = encode_address(state[b"account_2"])
        state[b"account_3"] = encode_address(state[b"account_3"])
        state[b"account_4"] = encode_address(state[b"account_4"])
        state[b"node_manager_0"] = encode_address(state[b"node_manager_0"])
        state[b"node_manager_1"] = encode_address(state[b"node_manager_1"])
        state[b"node_manager_2"] = encode_address(state[b"node_manager_2"])
        state[b"node_manager_3"] = encode_address(state[b"node_manager_3"])
        state[b"node_manager_4"] = encode_address(state[b"node_manager_4"])
        state[b"manager"] = encode_address(state[b"manager"])
        state[b"stake_manager"] = encode_address(state[b"stake_manager"])
        if b"proposed_manager" in state:
            state[b"proposed_manager"] = encode_address(state[b"proposed_manager"])
        state[b"fee_collector"] = encode_address(state[b"fee_collector"])
        return state

    def go_online(self, node_index, vote_pk, selection_pk, state_proof_pk, vote_first, vote_last, vote_key_dilution, fee):
        account_address = encode_address(self.get_global(b"account_%i" % node_index))
        # Use the user keys for signing transactions from the account_address
        self.keys[account_address] = self.keys[self.user_address]
        sp = self.get_suggested_params()
        transactions = [
            transaction.PaymentTxn(
                sender=self.user_address,
                receiver=account_address,
                sp=sp,
                amt=fee
            ) if fee else None,
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["change_online_status", node_index],
                accounts=[
                ],
                foreign_assets=[
                ]
            ),
            transaction.KeyregOnlineTxn(
                sender=account_address,
                sp=sp,
                rekey_to=self.application_address,
                votekey=vote_pk,
                selkey=selection_pk,
                votefst=vote_first,
                votelst=vote_last,
                votekd=vote_key_dilution,
                sprfkey=state_proof_pk,
            )
        ]
        if fee:
            transactions[2].fee = fee
        return self._submit(transactions, additional_fees=1)

    def go_offline(self, node_index):
        account_address = encode_address(self.get_global(b"account_%i" % node_index))
        # Use the user keys for signing transactions from the account_address
        self.keys[account_address] = self.keys[self.user_address]
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["change_online_status", node_index],
                accounts=[
                ],
                foreign_assets=[
                ]
            ),
            transaction.KeyregOfflineTxn(
                sender=account_address,
                sp=sp,
                rekey_to=self.application_address,
            )
        ]
        return self._submit(transactions, additional_fees=1)

    def set_node_manager(self, node_index, node_manager_address):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_node_manager", node_index, decode_address(node_manager_address)],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def set_fee_collector(self, new_fee_collector):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_fee_collector", decode_address(new_fee_collector)],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def set_protocol_fee(self, fee_amount):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_protocol_fee", fee_amount],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def set_max_account_balance(self, max_amount):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_max_account_balance", max_amount],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def propose_manager(self, new_manager):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["propose_manager", decode_address(new_manager)],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def accept_manager(self):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["accept_manager"],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def set_stake_manager(self, new_stake_manager):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["set_stake_manager", decode_address(new_stake_manager)],
                accounts=[
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=0)

    def move_stake(self, from_node_index, to_node_index, amount):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["move_stake", from_node_index, to_node_index, amount],
                accounts=[
                    encode_address(self.get_global(b"account_1")),
                    encode_address(self.get_global(b"account_2")),
                    encode_address(self.get_global(b"account_3")),
                    encode_address(self.get_global(b"account_4")),
                ],
                foreign_assets=[]
            ),
        ]
        return self._submit(transactions, additional_fees=1)

    def claim_protocol_rewards(self):
        sp = self.get_suggested_params()
        transactions = [
            transaction.ApplicationCallTxn(
                sender=self.user_address,
                on_complete=transaction.OnComplete.NoOpOC,
                sp=sp,
                index=self.app_id,
                app_args=["claim_protocol_rewards"],
                accounts=[
                   encode_address(self.get_global(b"fee_collector")),
                ],
                foreign_assets=[
                    self.get_global(b"talgo_asset_id"),
                ]
            ),
        ]
        return self._submit(transactions, additional_fees=1)

import time
from typing import Optional

import requests
from algosdk.encoding import encode_address, decode_address
from algosdk.v2client.algod import AlgodClient

from tinyman.compat import SuggestedParams
from tinyman.compat import wait_for_confirmation
from tinyman.governance.constants import TESTNET_TINY_ASSET_ID, TESTNET_VAULT_APP_ID, WEEK, TESTNET_REWARDS_APP_ID, TESTNET_STAKING_VOTING_APP_ID, TESTNET_PROPOSAL_VOTING_APP_ID, \
    MAINNET_TINY_ASSET_ID, MAINNET_VAULT_APP_ID, MAINNET_REWARDS_APP_ID, MAINNET_STAKING_VOTING_APP_ID, MAINNET_PROPOSAL_VOTING_APP_ID
from tinyman.governance.proposal_voting.constants import ACCOUNT_ATTENDANCE_SHEET_BOX_SIZE, EXECUTION_HASH_SIZE
from tinyman.governance.proposal_voting.exceptions import InsufficientTinyPower
from tinyman.governance.proposal_voting.storage import get_proposal, ProposalVotingAppGlobalState
from tinyman.governance.proposal_voting.transactions import prepare_create_proposal_transactions, prepare_cast_vote_transactions
from tinyman.governance.rewards.constants import REWARD_CLAIM_SHEET_BOX_SIZE
from tinyman.governance.rewards.storage import get_reward_histories, RewardsAppGlobalState, get_reward_history_index_at, get_reward_claim_sheet
from tinyman.governance.rewards.transactions import prepare_claim_reward_transactions, prepare_create_reward_period_transactions
from tinyman.governance.staking_voting.storage import get_staking_distribution_proposal, get_staking_attendance_sheet_box_name, StakingVotingAppGlobalState
from tinyman.governance.staking_voting.transactions import prepare_cast_vote_for_staking_distribution_proposal_transactions
from tinyman.governance.utils import get_global_state, get_all_box_names, box_exists
from tinyman.governance.vault.constants import MAX_LOCK_TIME, MIN_LOCK_TIME
from tinyman.governance.vault.exceptions import ShortLockEndTime, TooLongLockEndTime
from tinyman.governance.vault.storage import get_last_total_powers_indexes, get_power_index_at, get_account_state, get_slope_change, get_account_powers, get_all_total_powers, \
    VaultAppGlobalState
from tinyman.governance.vault.transactions import prepare_create_lock_transactions, prepare_increase_lock_amount_transactions, prepare_extend_lock_end_time_transactions, \
    prepare_create_checkpoints_transactions, prepare_withdraw_transactions
from tinyman.governance.vault.utils import get_bias, get_cumulative_power_delta, get_start_timestamp_of_week
from tinyman.optin import prepare_asset_optin_transactions
from tinyman.utils import TransactionGroup, generate_app_call_note


class TinymanGovernanceClient:
    def __init__(
        self,
        algod_client: AlgodClient,
        tiny_asset_id: int,
        vault_app_id: int,
        rewards_app_id: int,
        staking_voting_app_id: int,
        proposal_voting_app_id: int,
        api_base_url: Optional[str] = None,
        user_address: Optional[str] = None,
        client_name: Optional[str] = None,
    ):
        self.algod = algod_client
        self.tiny_asset_id = tiny_asset_id
        self.vault_app_id = vault_app_id
        self.rewards_app_id = rewards_app_id
        self.staking_voting_app_id = staking_voting_app_id
        self.proposal_voting_app_id = proposal_voting_app_id
        self.api_base_url = api_base_url
        self.user_address = user_address
        self.client_name = client_name

    def submit(self, transaction_group, wait=False):
        try:
            txid = self.algod.send_transactions(transaction_group.signed_transactions)
        except Exception as e:
            self.handle_error(e, transaction_group)
        if wait:
            txn_info = wait_for_confirmation(self.algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def handle_error(self, exception, transaction_group):
        error_message = str(exception)
        raise Exception(error_message) from None

    def prepare_asset_optin_transactions(
        self, asset_id, user_address=None, suggested_params=None
    ):
        user_address = user_address or self.user_address
        if suggested_params is None:
            suggested_params = self.algod.suggested_params()
        txn_group = prepare_asset_optin_transactions(
            asset_id=asset_id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def asset_is_opted_in(self, asset_id, user_address=None):
        user_address = user_address or self.user_address

        if asset_id == 0:
            # ALGO
            return True

        account_info = self.algod.account_info(user_address)
        for a in account_info.get("assets", []):
            if a["asset-id"] == asset_id:
                return True
        return False

    def generate_app_call_note(self, client_name: Optional[str] = None):
        note = generate_app_call_note(
            dapp_name="tinyman-governance",
            version="v1",
            client_name=client_name or self.client_name,
        )
        return note

    def get_required_tiny_power_to_create_proposal(self) -> int:
        voting_app_global_state = self.fetch_proposal_voting_app_global_state()
        required_tiny_power = voting_app_global_state.proposal_threshold

        if voting_app_global_state.proposal_threshold_numerator:
            total_tiny_power = self.get_total_tiny_power()
            required_tiny_power = max(required_tiny_power, ((total_tiny_power * voting_app_global_state.proposal_threshold_numerator) // 100) + 1)

        return required_tiny_power

    def get_tiny_power(self, address: Optional[str] = None, timestamp: Optional[int] = None) -> int:
        address = address or self.user_address

        if timestamp is None:
            timestamp = int(time.time())

        account_state = self.fetch_account_state(address)
        if account_state is None:
            return 0

        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )
        account_power_index = get_power_index_at(account_powers, timestamp)
        if account_power_index is None:
            return 0

        account_power = account_powers[account_power_index]
        time_delta = timestamp - account_power.timestamp
        tiny_power = max(account_power.bias - get_bias(account_power.slope, time_delta), 0)
        return tiny_power

    def get_cumulative_tiny_power(self, address: Optional[str] = None, timestamp: Optional[int] = None):
        address = address or self.user_address

        if timestamp is None:
            timestamp = int(time.time())

        account_state = self.fetch_account_state(address)
        if account_state is None:
            return 0

        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )
        account_power_index = get_power_index_at(account_powers, timestamp)
        if account_power_index is None:
            return 0

        account_power = account_powers[account_power_index]
        time_delta = timestamp - account_power.timestamp
        cumulative_power_delta = get_cumulative_power_delta(account_power.bias, account_power.slope, time_delta)
        cumulative_tiny_power = account_power.cumulative_power + cumulative_power_delta
        return cumulative_tiny_power

    def get_total_tiny_power(self, timestamp: Optional[int] = None):
        if timestamp is None:
            timestamp = int(time.time())

        vault_app_global_state = self.fetch_vault_app_global_state()
        total_powers = get_all_total_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            total_power_count=vault_app_global_state.total_power_count
        )
        total_power_index = get_power_index_at(total_powers, timestamp)
        if total_power_index is None:
            return 0

        # Given timestamp can be in the future, apply slope changes
        total_power = total_powers[total_power_index]
        total_power_week_index = total_power.timestamp // WEEK
        new_week_count = timestamp // WEEK - total_power_week_index
        week_timestamps = [(total_power_week_index + i) * WEEK for i in range(1, new_week_count + 1)]
        time_ranges = list(zip([total_power.timestamp] + week_timestamps, week_timestamps + [timestamp]))

        tiny_power = total_power.bias
        slope = total_power.slope

        for time_range in time_ranges:
            time_delta = time_range[1] - time_range[0]
            bias_delta = get_bias(slope, time_delta)
            tiny_power = max(tiny_power - bias_delta, 0)
            slope_delta = get_slope_change(algod=self.algod, app_id=self.vault_app_id, timestamp=time_range[1]) or 0
            slope = max(slope - slope_delta, 0)
            if tiny_power == 0 or slope == 0:
                tiny_power = 0
                slope = 0

        return tiny_power

    def fetch_account_state(self, user_address: Optional[str] = None):
        user_address = user_address or self.user_address

        account_state = get_account_state(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=user_address
        )
        return account_state

    def fetch_vault_app_global_state(self) -> VaultAppGlobalState:
        data = get_global_state(
            algod=self.algod,
            app_id=self.vault_app_id
        )
        return VaultAppGlobalState(**data)

    def fetch_rewards_app_global_state(self) -> RewardsAppGlobalState:
        data = get_global_state(
            algod=self.algod,
            app_id=self.rewards_app_id
        )
        data["manager"] = encode_address(data["manager"])
        data["rewards_manager"] = encode_address(data["rewards_manager"])
        return RewardsAppGlobalState(**data)

    def fetch_staking_voting_app_global_state(self) -> StakingVotingAppGlobalState:
        data = get_global_state(
            algod=self.algod,
            app_id=self.staking_voting_app_id
        )
        return StakingVotingAppGlobalState(**data)

    def fetch_proposal_voting_app_global_state(self) -> ProposalVotingAppGlobalState:
        data = get_global_state(
            algod=self.algod,
            app_id=self.proposal_voting_app_id
        )
        return ProposalVotingAppGlobalState(**data)

    def fetch_proposal(self, proposal_id: str):
        proposal = get_proposal(
            algod=self.algod,
            app_id=self.proposal_voting_app_id,
            proposal_id=proposal_id
        )
        return proposal

    def fetch_staking_distribution_proposal(self, proposal_id: str):
        proposal = get_staking_distribution_proposal(
            algod=self.algod,
            app_id=self.staking_voting_app_id,
            proposal_id=proposal_id
        )
        return proposal

    # Vault
    def prepare_create_lock_transactions(
            self,
            locked_amount: int,
            lock_end_time: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if lock_end_time < int(time.time()) + MIN_LOCK_TIME:
            raise ShortLockEndTime

        if lock_end_time > int(time.time()) + MAX_LOCK_TIME:
            raise TooLongLockEndTime

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        vault_app_global_state = self.fetch_vault_app_global_state()
        slope_change_at_lock_end_time = get_slope_change(algod=self.algod, app_id=self.vault_app_id, timestamp=lock_end_time)

        txn_group = prepare_create_lock_transactions(
            vault_app_id=self.vault_app_id,
            tiny_asset_id=self.tiny_asset_id,
            sender=user_address,
            locked_amount=locked_amount,
            lock_end_time=lock_end_time,
            vault_app_global_state=vault_app_global_state,
            account_state=account_state,
            slope_change_at_lock_end_time=slope_change_at_lock_end_time,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_increase_lock_amount_transactions(
            self,
            locked_amount: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        vault_app_global_state = self.fetch_vault_app_global_state()
        last_total_power_box_index, _ = get_last_total_powers_indexes(vault_app_global_state.total_power_count)

        txn_group = prepare_increase_lock_amount_transactions(
            vault_app_id=self.vault_app_id,
            tiny_asset_id=self.tiny_asset_id,
            sender=user_address,
            locked_amount=locked_amount,
            vault_app_global_state=vault_app_global_state,
            account_state=account_state,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_extend_lock_end_time_transactions(
            self,
            new_lock_end_time: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        vault_app_global_state = self.fetch_vault_app_global_state()
        slope_change_at_new_lock_end_time = get_slope_change(algod=self.algod, app_id=self.vault_app_id, timestamp=new_lock_end_time)

        txn_group = prepare_extend_lock_end_time_transactions(
            vault_app_id=self.vault_app_id,
            sender=user_address,
            new_lock_end_time=new_lock_end_time,
            vault_app_global_state=vault_app_global_state,
            account_state=account_state,
            slope_change_at_new_lock_end_time=slope_change_at_new_lock_end_time,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_increase_lock_amount_and_extend_lock_end_time_transactions(
            self,
            locked_amount: int,
            new_lock_end_time: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        vault_app_global_state = self.fetch_vault_app_global_state()
        slope_change_at_new_lock_end_time = get_slope_change(algod=self.algod, app_id=self.vault_app_id, timestamp=new_lock_end_time)

        increase_lock_amount_txn_group = prepare_increase_lock_amount_transactions(
            vault_app_id=self.vault_app_id,
            tiny_asset_id=self.tiny_asset_id,
            sender=user_address,
            locked_amount=locked_amount,
            vault_app_global_state=vault_app_global_state,
            account_state=account_state,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        account_state.power_count += 1
        vault_app_global_state.total_power_count += 1

        extend_lock_end_time_txn_group = prepare_extend_lock_end_time_transactions(
            vault_app_id=self.vault_app_id,
            sender=user_address,
            new_lock_end_time=new_lock_end_time,
            vault_app_global_state=vault_app_global_state,
            account_state=account_state,
            slope_change_at_new_lock_end_time=slope_change_at_new_lock_end_time,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        txn_group = increase_lock_amount_txn_group + extend_lock_end_time_txn_group
        return txn_group

    def prepare_create_checkpoints_transactions(
        self,
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        vault_app_global_state = self.fetch_vault_app_global_state()
        txn_group = prepare_create_checkpoints_transactions(
            vault_app_id=self.vault_app_id,
            sender=user_address,
            vault_app_global_state=vault_app_global_state,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_withdraw_transactions(
        self,
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        txn_group = prepare_withdraw_transactions(
            vault_app_id=self.vault_app_id,
            tiny_asset_id=self.tiny_asset_id,
            sender=user_address,
            account_state=account_state,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    # Rewards
    def prepare_create_reward_period_transactions(
            self,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        vault_app_global_state = self.fetch_vault_app_global_state()
        rewards_app_global_state = self.fetch_rewards_app_global_state()

        total_powers = get_all_total_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            total_power_count=vault_app_global_state.total_power_count
        )

        period_start_timestamp = rewards_app_global_state.first_period_timestamp + (rewards_app_global_state.reward_period_count * WEEK)
        period_end_timestamp = period_start_timestamp + WEEK
        total_power_period_start_index = get_power_index_at(total_powers, period_start_timestamp)
        total_power_period_end_index = get_power_index_at(total_powers, period_end_timestamp)

        reward_histories = get_reward_histories(algod=self.algod, app_id=self.rewards_app_id, reward_history_count=rewards_app_global_state.reward_history_count)
        reward_history_index = get_reward_history_index_at(reward_histories, period_start_timestamp)

        txn_group = prepare_create_reward_period_transactions(
            rewards_app_id=self.rewards_app_id,
            vault_app_id=self.vault_app_id,
            sender=user_address,
            rewards_app_global_state=rewards_app_global_state,
            reward_history_index=reward_history_index,
            total_power_period_start_index=total_power_period_start_index,
            total_power_period_end_index=total_power_period_end_index,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_claim_reward_transactions(
            self,
            period_index_start: int,
            period_count: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        rewards_app_global_state = self.fetch_rewards_app_global_state()
        assert period_index_start + period_count <= rewards_app_global_state.reward_period_count

        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=user_address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )

        claim_period_start_timestamp = rewards_app_global_state.first_period_timestamp + (period_index_start * WEEK)
        claim_period_end_timestamp = rewards_app_global_state.first_period_timestamp + (period_index_start + period_count) * WEEK

        account_power_indexes = []
        for timestamp in range(claim_period_start_timestamp, claim_period_end_timestamp + 1, WEEK):
            account_power_index = (get_power_index_at(account_powers, timestamp) or 0)
            account_power_indexes.append(account_power_index)

        create_reward_claim_sheet = False
        account_reward_claim_sheet_box_indexes = {
            period_index_start // (REWARD_CLAIM_SHEET_BOX_SIZE * 8),
            (period_index_start + period_count) // (REWARD_CLAIM_SHEET_BOX_SIZE * 8)
        }
        for account_reward_claim_sheet_box_index in account_reward_claim_sheet_box_indexes:
            reward_claim_sheet = get_reward_claim_sheet(
                algod=self.algod,
                app_id=self.rewards_app_id,
                address=user_address,
                account_reward_claim_sheet_box_index=account_reward_claim_sheet_box_index
            )
            if reward_claim_sheet is None:
                create_reward_claim_sheet = True
                break

        txn_group = prepare_claim_reward_transactions(
            rewards_app_id=self.rewards_app_id,
            vault_app_id=self.vault_app_id,
            tiny_asset_id=self.tiny_asset_id,
            sender=user_address,
            period_index_start=period_index_start,
            period_count=period_count,
            account_power_indexes=account_power_indexes,
            create_reward_claim_sheet=create_reward_claim_sheet,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def get_pending_reward_period_indexes(
            self,
            user_address: Optional[str] = None,
    ) -> list[int]:
        user_address = user_address or self.user_address

        reward_claim_sheet = get_reward_claim_sheet(
            algod=self.algod,
            app_id=self.rewards_app_id,
            address=user_address,
            account_reward_claim_sheet_box_index=0
        )
        if reward_claim_sheet is not None:
            claimed_reward_period_indexes = [index for index, value in enumerate(reward_claim_sheet.claim_sheet) if value]
        else:
            claimed_reward_period_indexes = []

        rewards_app_global_state = self.fetch_rewards_app_global_state()
        account_state = self.fetch_account_state(self.user_address)
        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=user_address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )

        reward_period_indexes = []
        period_timestamp_min = max([account_powers[0].timestamp, rewards_app_global_state.first_period_timestamp])
        period_timestamp_max = get_start_timestamp_of_week(min([account_powers[-1].lock_end_timestamp, int(time.time())]))

        for timestamp in range(period_timestamp_min, period_timestamp_max + WEEK, WEEK):
            timestamp_start = timestamp
            timestamp_end = timestamp_start + WEEK
            if timestamp_end > int(time.time()):
                break

            index_start = get_power_index_at(account_powers, timestamp_start)
            cumulative_power_start = account_powers[index_start].cumulative_power_at(timestamp_start)

            index_end = get_power_index_at(account_powers, timestamp_end)
            cumulative_power_end = account_powers[index_end].cumulative_power_at(timestamp_end)

            cumulative_power_delta = cumulative_power_end - cumulative_power_start
            if cumulative_power_delta:
                reward_period_index = timestamp_start // WEEK - rewards_app_global_state.first_period_timestamp // WEEK
                reward_period_indexes.append(reward_period_index)

        pending_period_indexes = [pi for pi in reward_period_indexes if pi not in claimed_reward_period_indexes]
        return pending_period_indexes

    def prepare_create_proposal_transactions(
            self,
            proposal_id: str,
            execution_hash: Optional[str] = None,
            executor: Optional[str] = None,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address
        account_tiny_power = self.get_tiny_power()

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        if required_tiny_power := self.get_required_tiny_power_to_create_proposal():
            if account_tiny_power < required_tiny_power:
                raise InsufficientTinyPower()

        if executor:
            executor = decode_address(executor)
        else:
            executor = self.fetch_proposal_voting_app_global_state().proposal_manager

        if execution_hash:
            assert len(execution_hash) == EXECUTION_HASH_SIZE, "Invalid execution hash."

        vault_app_global_state = self.fetch_vault_app_global_state()
        txn_group = prepare_create_proposal_transactions(
            proposal_voting_app_id=self.proposal_voting_app_id,
            vault_app_id=self.vault_app_id,
            sender=user_address,
            proposal_id=proposal_id,
            vault_app_global_state=vault_app_global_state,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
            execution_hash=execution_hash,
            executor=executor,
        )
        return txn_group

    def prepare_cast_vote_transactions(
            self,
            proposal_id: str,
            vote: int,
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        proposal = self.fetch_proposal(proposal_id)
        account_state = self.fetch_account_state(user_address)

        assert account_state is not None
        assert proposal.is_approved
        assert proposal.voting_start_timestamp
        assert proposal.voting_start_timestamp <= int(time.time()) <= proposal.voting_end_timestamp

        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=user_address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )
        account_power_index = get_power_index_at(account_powers, proposal.creation_timestamp)

        account_attendance_sheet_box_index = proposal.index // (ACCOUNT_ATTENDANCE_SHEET_BOX_SIZE * 8)
        account_attendance_sheet_box_name = get_staking_attendance_sheet_box_name(address=user_address, box_index=account_attendance_sheet_box_index)
        create_attendance_sheet_box = not box_exists(self.algod, self.proposal_voting_app_id, account_attendance_sheet_box_name)

        txn_group = prepare_cast_vote_transactions(
            proposal_voting_app_id=self.proposal_voting_app_id,
            vault_app_id=self.vault_app_id,
            sender=user_address,
            proposal_id=proposal_id,
            proposal=proposal,
            vote=vote,
            account_power_index=account_power_index,
            create_attendance_sheet_box=create_attendance_sheet_box,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def prepare_cast_vote_for_staking_distribution_proposal_transactions(
            self,
            proposal_id: str,
            votes: list[int],
            asset_ids: list[int],
            user_address: Optional[str] = None,
            suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.user_address

        if suggested_params is None:
            suggested_params = self.algod.suggested_params()

        account_state = self.fetch_account_state(user_address)
        staking_distribution_proposal = self.fetch_staking_distribution_proposal(proposal_id)
        app_box_names = get_all_box_names(self.algod, self.staking_voting_app_id)

        account_powers = get_account_powers(
            algod=self.algod,
            app_id=self.vault_app_id,
            address=user_address,
            power_count=account_state.power_count,
            deleted_power_count=account_state.deleted_power_count,
        )
        account_power_index = get_power_index_at(account_powers, staking_distribution_proposal.creation_timestamp)

        txn_group = prepare_cast_vote_for_staking_distribution_proposal_transactions(
            staking_voting_app_id=self.staking_voting_app_id,
            vault_app_id=self.vault_app_id,
            sender=user_address,
            proposal_id=proposal_id,
            proposal=staking_distribution_proposal,
            votes=votes,
            asset_ids=asset_ids,
            account_power_index=account_power_index,
            app_box_names=app_box_names,
            suggested_params=suggested_params,
            app_call_note=self.generate_app_call_note(),
        )
        return txn_group

    def upload_proposal_metadata(self, proposal_id, metadata):
        payload = {
            "proposal_id": proposal_id,
            "metadata": metadata
        }
        r = requests.post(
            self.api_base_url + "v1/governance/proposals/", json=payload
        )
        r.raise_for_status()


class TinymanGovernanceTestnetClient(TinymanGovernanceClient):
    def __init__(
        self,
        algod_client: AlgodClient,
        user_address: Optional[str] = None,
        client_name: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        super().__init__(
            algod_client,
            tiny_asset_id=TESTNET_TINY_ASSET_ID,
            vault_app_id=TESTNET_VAULT_APP_ID,
            rewards_app_id=TESTNET_REWARDS_APP_ID,
            staking_voting_app_id=TESTNET_STAKING_VOTING_APP_ID,
            proposal_voting_app_id=TESTNET_PROPOSAL_VOTING_APP_ID,
            user_address=user_address,
            client_name=client_name,
            api_base_url=api_base_url or "https://testnet.analytics.tinyman.org/api/",
        )


class TinymanGovernanceMainnetClient(TinymanGovernanceClient):
    def __init__(
        self,
        algod_client: AlgodClient,
        user_address: Optional[str] = None,
        client_name: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        super().__init__(
            algod_client,
            tiny_asset_id=MAINNET_TINY_ASSET_ID,
            vault_app_id=MAINNET_VAULT_APP_ID,
            rewards_app_id=MAINNET_REWARDS_APP_ID,
            staking_voting_app_id=MAINNET_STAKING_VOTING_APP_ID,
            proposal_voting_app_id=MAINNET_PROPOSAL_VOTING_APP_ID,
            user_address=user_address,
            client_name=client_name,
            api_base_url=api_base_url or "https://mainnet.analytics.tinyman.org/api/",
        )

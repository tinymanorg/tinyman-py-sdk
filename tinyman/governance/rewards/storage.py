import math
from dataclasses import dataclass
from typing import Optional

from tinyman.governance.constants import WEEK
from tinyman.governance.rewards.constants import REWARD_HISTORY_BOX_PREFIX, REWARD_HISTORY_BOX_ARRAY_LEN, REWARD_HISTORY_SIZE, REWARD_CLAIM_SHEET_BOX_PREFIX, REWARD_PERIOD_BOX_PREFIX, REWARD_PERIOD_BOX_ARRAY_LEN, REWARD_PERIOD_SIZE
from tinyman.governance.utils import get_raw_box_value, check_nth_bit_from_left
from tinyman.utils import int_to_bytes, bytes_to_int
from algosdk.encoding import decode_address


@dataclass
class RewardsAppGlobalState:
    tiny_asset_id: int
    vault_app_id: int
    reward_history_count: int
    reward_period_count: int
    first_period_timestamp: int
    manager: str
    rewards_manager: str

    def get_reward_period_index(self, timestamp):
        reward_period_index = timestamp // WEEK - self.first_period_timestamp // WEEK
        return reward_period_index

    @property
    def free_reward_history_space_count(self) -> int:
        remainder = self.reward_history_count % REWARD_HISTORY_BOX_ARRAY_LEN
        return REWARD_HISTORY_BOX_ARRAY_LEN - remainder if remainder > 0 else 0


@dataclass
class RewardPeriod:
    total_reward_amount: int
    total_cumulative_power_delta: int


@dataclass
class RewardHistory:
    timestamp: int
    reward_amount: int


@dataclass
class RewardClaimSheet:
    value: bytes

    @property
    def claim_sheet(self) -> list[bool]:
        return [check_nth_bit_from_left(self.value, index) for index in range(0, (len(self.value) * 8))]

    def is_reward_claimed_for_period(self, period_index) -> bool:
        return check_nth_bit_from_left(self.value, period_index)


def get_reward_history_box_name(box_index) -> bytes:
    return REWARD_HISTORY_BOX_PREFIX + int_to_bytes(box_index)


def get_reward_period_box_name(box_index) -> bytes:
    return REWARD_PERIOD_BOX_PREFIX + int_to_bytes(box_index)


def get_account_reward_claim_sheet_box_name(address: str, box_index: int) -> bytes:
    account_reward_claim_sheet_box_name = REWARD_CLAIM_SHEET_BOX_PREFIX + decode_address(address) + int_to_bytes(box_index)
    return account_reward_claim_sheet_box_name


def parse_box_reward_history(raw_box) -> list[RewardHistory]:
    box_size = REWARD_HISTORY_SIZE
    rows = [raw_box[i:i + box_size] for i in range(0, len(raw_box), box_size)]
    reward_histories = []
    for row in rows:
        if row == (b'\x00' * box_size):
            break

        reward_histories.append(
            RewardHistory(
                timestamp=bytes_to_int(row[:8]),
                reward_amount=bytes_to_int(row[8:16]),
            )
        )
    return reward_histories


def get_reward_histories(algod, app_id: int, reward_history_count: int) -> list[RewardHistory]:
    box_count = math.ceil(reward_history_count / REWARD_HISTORY_BOX_ARRAY_LEN)

    reward_histories = []
    for box_index in range(box_count):
        box_name = get_reward_history_box_name(box_index=box_index)
        raw_box = get_raw_box_value(algod, app_id, box_name)
        reward_histories.extend(parse_box_reward_history(raw_box))
    return reward_histories


def get_reward_history_index_at(reward_histories: list[RewardHistory], timestamp: int) -> Optional[int]:
    reward_history_index = None

    for index, reward_history in enumerate(reward_histories):
        if timestamp >= reward_history.timestamp:
            reward_history_index = index
        else:
            break

    return reward_history_index


def parse_box_reward_period(raw_box) -> list[RewardPeriod]:
    box_size = REWARD_PERIOD_SIZE
    rows = [raw_box[i:i + box_size] for i in range(0, len(raw_box), box_size)]
    reward_periods = []
    for row in rows:
        if row == (b'\x00' * box_size):
            break

        reward_periods.append(
            RewardPeriod(
                total_reward_amount=bytes_to_int(row[:8]),
                total_cumulative_power_delta=bytes_to_int(row[8:24]),
            )
        )
    return reward_periods


def get_reward_periods(algod, app_id: int, reward_period_count: int) -> list[RewardPeriod]:
    box_count = math.ceil(reward_period_count / REWARD_PERIOD_BOX_ARRAY_LEN)

    reward_periods = []
    for box_index in range(box_count):
        box_name = get_reward_period_box_name(box_index=box_index)
        raw_box = get_raw_box_value(algod, app_id, box_name)
        reward_periods.extend(parse_box_reward_period(raw_box))
    return reward_periods


def get_reward_claim_sheet(algod, app_id: int, address: str, account_reward_claim_sheet_box_index: int) -> Optional[RewardClaimSheet]:
    box_name = get_account_reward_claim_sheet_box_name(address=address, box_index=account_reward_claim_sheet_box_index)
    raw_box = get_raw_box_value(algod, app_id, box_name)
    if raw_box is None:
        return None
    return RewardClaimSheet(value=raw_box)

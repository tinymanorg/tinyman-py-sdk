import math
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from algosdk.encoding import decode_address

from tinyman.governance.utils import get_raw_box_value
from tinyman.governance.vault.constants import TOTAL_POWERS, SLOPE_CHANGES, ACCOUNT_POWER_BOX_ARRAY_LEN, TOTAL_POWER_BOX_ARRAY_LEN, ACCOUNT_POWER_SIZE, TOTAL_POWER_SIZE, TWO_TO_THE_64
from tinyman.utils import int_to_bytes, bytes_to_int


@dataclass
class VaultAppGlobalState:
    tiny_asset_id: int
    total_locked_amount: int
    total_power_count: int
    last_total_power_timestamp: int

    @property
    def free_total_power_space_count(self) -> int:
        remainder = self.total_power_count % TOTAL_POWER_BOX_ARRAY_LEN
        return TOTAL_POWER_BOX_ARRAY_LEN - remainder if remainder > 0 else 0

    @property
    def last_total_power_box_index(self) -> int:
        return get_last_total_powers_indexes(self.total_power_count)[0]

    @property
    def last_total_power_array_index(self) -> int:
        return get_last_total_powers_indexes(self.total_power_count)[1]


@dataclass
class AccountState:
    locked_amount: int
    lock_end_time: int
    power_count: int
    deleted_power_count: int

    @property
    def free_account_power_space_count(self) -> int:
        remainder = self.power_count % ACCOUNT_POWER_BOX_ARRAY_LEN
        return ACCOUNT_POWER_BOX_ARRAY_LEN - remainder if remainder > 0 else 0

    @property
    def last_account_power_box_index(self) -> int:
        return get_last_account_power_box_indexes(self.power_count)[0]

    @property
    def last_account_power_array_index(self) -> int:
        return get_last_account_power_box_indexes(self.power_count)[1]


@dataclass
class AccountPower:
    bias: int
    timestamp: int
    slope: int
    cumulative_power: int

    @property
    def lock_end_timestamp(self):
        lock_duration = self.bias * TWO_TO_THE_64 // self.slope
        return self.timestamp + lock_duration

    def cumulative_power_at(self, timestamp: int) -> int:
        from tinyman.governance.vault.utils import get_cumulative_power_delta

        time_delta = timestamp - self.timestamp
        assert time_delta >= 0
        cumulative_power_delta = get_cumulative_power_delta(self.bias, self.slope, time_delta)
        return self.cumulative_power + cumulative_power_delta


@dataclass
class TotalPower:
    bias: int
    timestamp: int
    slope: int
    cumulative_power: int


@dataclass
class SlopeChange:
    slope_delta: Optional[int]


def get_account_state_box_name(address: str) -> bytes:
    return decode_address(address)


def get_total_power_box_name(box_index: int) -> bytes:
    return TOTAL_POWERS + int_to_bytes(box_index)


def get_account_power_box_name(address: str, box_index: int) -> bytes:
    return decode_address(address) + int_to_bytes(box_index)


def get_slope_change_box_name(timestamp: int) -> bytes:
    return SLOPE_CHANGES + int_to_bytes(timestamp)


def parse_box_account_state(raw_box: bytes) -> AccountState:
    return AccountState(
        locked_amount=bytes_to_int(raw_box[:8]),
        lock_end_time=bytes_to_int(raw_box[8:16]),
        power_count=bytes_to_int(raw_box[16:24]),
        deleted_power_count=bytes_to_int(raw_box[24:32]),
    )


def parse_box_account_power(raw_box: bytes) -> list[AccountPower]:
    box_size = ACCOUNT_POWER_SIZE
    rows = [raw_box[i:i + box_size] for i in range(0, len(raw_box), box_size)]
    powers = []
    for row in rows:
        if row == (b'\x00' * box_size):
            break

        powers.append(
            AccountPower(
                bias=bytes_to_int(row[:8]),
                timestamp=bytes_to_int(row[8:16]),
                slope=bytes_to_int(row[16:32]),
                cumulative_power=bytes_to_int(row[32:48]),
            )
        )
    return powers


def parse_box_total_power(raw_box: bytes) -> list[TotalPower]:
    box_size = TOTAL_POWER_SIZE
    rows = [raw_box[i:i + box_size] for i in range(0, len(raw_box), box_size)]
    powers = []
    for row in rows:
        if row == (b'\x00' * box_size):
            break

        powers.append(
            TotalPower(
                bias=bytes_to_int(row[:8]),
                timestamp=bytes_to_int(row[8:16]),
                slope=bytes_to_int(row[16:32]),
                cumulative_power=bytes_to_int(row[32:48]),
            )
        )
    return powers


def parse_box_slope_change(raw_box: bytes) -> SlopeChange:
    return SlopeChange(
        slope_delta=bytes_to_int(raw_box[:16]),
    )


def get_account_state(algod, app_id: int, address: str) -> Optional[AccountState]:
    box_name = get_account_state_box_name(address=address)
    raw_box = get_raw_box_value(algod, app_id, box_name)
    if not raw_box:
        return None
    return parse_box_account_state(raw_box)


def get_account_powers(algod, app_id, address: str, power_count: int, deleted_power_count: int):
    box_count = math.ceil(power_count / ACCOUNT_POWER_BOX_ARRAY_LEN)
    deleted_box_count = deleted_power_count // ACCOUNT_POWER_BOX_ARRAY_LEN

    account_powers = []
    for box_index in range(deleted_box_count, box_count):
        box_name = get_account_power_box_name(address=address, box_index=box_index)
        raw_box = get_raw_box_value(algod, app_id, box_name)
        account_powers.extend(parse_box_account_power(raw_box))
    return account_powers


def get_total_powers(algod, app_id: int, box_index: int) -> list[TotalPower]:
    box_name = get_total_power_box_name(box_index=box_index)
    box_value = get_raw_box_value(algod, app_id, box_name)
    total_powers = parse_box_total_power(box_value)
    return total_powers


def get_all_total_powers(algod, app_id: int, total_power_count: int) -> list[TotalPower]:
    box_count = math.ceil(total_power_count / TOTAL_POWER_BOX_ARRAY_LEN)
    immutable_box_count = total_power_count // TOTAL_POWER_BOX_ARRAY_LEN

    total_powers = []
    for box_index in range(box_count):
        box_name = get_total_power_box_name(box_index=box_index)
        is_box_immutable = box_index < immutable_box_count
        raw_box = get_raw_box_value(algod, app_id, box_name, cache=is_box_immutable)
        total_powers.extend(parse_box_total_power(raw_box))
    return total_powers


def get_slope_change(algod, app_id: int, timestamp: int) -> Optional[SlopeChange]:
    box_name = get_slope_change_box_name(timestamp=timestamp)
    raw_box = get_raw_box_value(algod, app_id, box_name)
    if raw_box is None:
        return None
    return parse_box_slope_change(raw_box)


def get_last_total_powers_indexes(total_power_count: int) -> Tuple[int, int]:
    last_index = total_power_count - 1
    box_index = last_index // TOTAL_POWER_BOX_ARRAY_LEN
    array_index = last_index % TOTAL_POWER_BOX_ARRAY_LEN
    return box_index, array_index


def is_total_power_box_full(total_power_count: int) -> bool:
    return (total_power_count % TOTAL_POWER_BOX_ARRAY_LEN) == 0


def get_last_account_power_box_indexes(power_count: int) -> Tuple[int, int]:
    last_index = power_count - 1
    box_index = last_index // ACCOUNT_POWER_BOX_ARRAY_LEN
    array_index = last_index % ACCOUNT_POWER_BOX_ARRAY_LEN
    return box_index, array_index


def is_account_power_box_full(account_power_count: int) -> bool:
    return (account_power_count % TOTAL_POWER_BOX_ARRAY_LEN) == 0


def get_power_index_at(powers: Union[list[AccountPower], list[TotalPower]], timestamp: int) -> Optional[int]:
    power_index = None

    for index, power in enumerate(powers):
        if timestamp >= power.timestamp:
            power_index = index
        else:
            break

    return power_index

from tinyman.governance.constants import WEEK
from tinyman.governance.vault.constants import TWO_TO_THE_64, MAX_LOCK_TIME


def get_slope(locked_amount):
    return locked_amount * TWO_TO_THE_64 // MAX_LOCK_TIME


def get_bias(slope, time_delta):
    assert time_delta >= 0
    return (slope * time_delta) // TWO_TO_THE_64


def get_start_timestamp_of_week(value):
    return (value // WEEK) * WEEK


def get_cumulative_power_delta(bias: int, slope: int, time_delta: int) -> int:
    bias_delta = get_bias(slope, time_delta)

    if bias_delta > bias:
        if slope:
            cumulative_power_delta = ((bias * bias) * TWO_TO_THE_64) // (slope * 2)
        else:
            cumulative_power_delta = 0
    else:
        new_bias = bias - bias_delta
        cumulative_power_delta = (bias + new_bias) * time_delta // 2
    return cumulative_power_delta


def get_cumulative_power(old_bias: int, new_bias: int, time_delta: int) -> int:
    """Calculate the cumulative power between two biases over a time period. Reference: vault_approval.get_cumulative_power_1()"""
    return (old_bias + new_bias) * time_delta // 2


def get_cumulative_power_2(bias: int, slope: int):
    """Calculate the cumulative power through the end of lock. Reference: vault_approval.get_cumulative_power_2()"""
    return ((bias * bias) * TWO_TO_THE_64) // (slope * 2)


def get_new_total_power_timestamps(old_timestamp, new_timestamp):
    assert old_timestamp <= new_timestamp

    timestamps = []
    week_timestamp = get_start_timestamp_of_week(old_timestamp) + WEEK
    while week_timestamp < new_timestamp:
        timestamps.append(week_timestamp)
        week_timestamp += WEEK
    timestamps.append(new_timestamp)

    return timestamps


def get_new_total_power_count(old_timestamp, new_timestamp):
    return len(get_new_total_power_timestamps(old_timestamp, new_timestamp))

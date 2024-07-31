from base64 import b64decode, b64encode
from datetime import datetime

from tinyman.utils import bytes_to_int
from tinyman.constants import YEAR, HOURS_PER_YEAR


def get_asset_pair_from_pool_app(algod, app_id):
    app = algod.application_info(app_id)
    global_state = {x["key"]: x["value"]["bytes"] for x in app["params"]["global-state"]}

    b = b64decode(global_state[b64encode(b"a").decode()])

    asset_id, f_asset_id = bytes_to_int(b[:8]), bytes_to_int(b[8:16])
    return asset_id, f_asset_id


def get_lending_pools(algod, pool_manager_app_id):
    # Get global state of lending manager app.
    app = algod.application_info(pool_manager_app_id)
    global_state = {x["key"]: x["value"]["bytes"] for x in app["params"]["global-state"]}

    # Concatanate all the global state values.
    data = b""
    for i in range(63):
        key = b64encode((i).to_bytes(1, "big")).decode()
        data += b64decode(global_state[key])  # 126 bytes

    # Iterate over the data and parse.
    pools = []
    for i in range(186):
        pool = parse_lending_pool_info(data[(42 * i): (42 * (i + 1))])

        if pool["pool_app_id"]:
            asset_id, f_asset_id = get_asset_pair_from_pool_app(algod, pool["pool_app_id"])
            pool["asset_id"] = asset_id
            pool["f_asset_id"] = f_asset_id

            pools.append(pool)

    return pools


def exp_by_squaring(x, n, scale):
    """Returns: x**n"""
    if n == 0:
        return scale

    y = scale
    while n > 1:
        if n % 2:
            y = (x * y) / scale
            n = (n - 1) // 2
        else:
            n = n // 2
        x = (x * x) / scale

    return int((x * y) / scale)


def calculate_borrow_interest_index(variable_borrow_interest_rate, old_variable_borrow_interest_index, timestamp: int):
    timedelta = int(datetime.now().timestamp()) - timestamp
    return int(old_variable_borrow_interest_index * exp_by_squaring(int(1e16) + variable_borrow_interest_rate / YEAR, timedelta, int(1e16)) / int(1e16))


def calculate_deposit_interest_index(deposit_interest_rate, old_deposit_interest_index, timestamp):
    timedelta = int(datetime.now().timestamp()) - timestamp
    return int(old_deposit_interest_index * (int(1e16) + (deposit_interest_rate * timedelta) / YEAR) / int(1e16))


def compound(rate, scale, period):
    return exp_by_squaring(scale + (rate / period), period, scale) - scale


def compound_every_second(rate, scale):
    return compound(rate, scale, YEAR)


def compound_every_hour(rate, scale):
    return compound(rate, scale, HOURS_PER_YEAR)


def parse_lending_pool_info(pool_data) -> dict:
    pool = {}
    pool["pool_app_id"] = bytes_to_int(pool_data[0:6])
    pool["variable_borrow_interest_rate"] = bytes_to_int(pool_data[6:14])
    pool["old_variable_borrow_interest_index"] = bytes_to_int(pool_data[14:22])
    pool["deposit_interest_rate"] = bytes_to_int(pool_data[22:30])
    pool["old_deposit_interest_index"] = bytes_to_int(pool_data[30:38])
    pool["old_timestamp"] = bytes_to_int(pool_data[38:42])

    pool["variable_borrow_interest_yield"] = compound_every_second(pool["variable_borrow_interest_rate"], int(1e16))
    pool["deposit_interest_yield"] = compound_every_hour(pool["deposit_interest_rate"], int(1e16))

    pool["variable_borrow_interest_index"] = calculate_borrow_interest_index(pool["variable_borrow_interest_rate"], pool["old_variable_borrow_interest_index"], pool["old_timestamp"])
    pool["deposit_interest_index"] = calculate_deposit_interest_index(pool["deposit_interest_rate"], pool["old_deposit_interest_index"], pool["old_timestamp"])

    return pool

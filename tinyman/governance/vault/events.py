from algosdk import abi

from tinyman.governance.event import Event

event_init = Event(
    name="init",
    args=[]
)

event_create_checkpoints = Event(
    name="create_checkpoints",
    args=[]
)

event_del_box = Event(
    name="box_del",
    args=[
        abi.Argument(arg_type="byte[]", name="box_name"),
    ]
)

event_delete_account_state = Event(
    name="delete_account_state",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="box_index_start"),
        abi.Argument(arg_type="uint64", name="box_count"),
    ]
)

event_delete_account_power_boxes = Event(
    name="delete_account_power_boxes",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="box_index_start"),
        abi.Argument(arg_type="uint64", name="box_count"),
    ]
)

event_create_lock = Event(
    name="create_lock",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="locked_amount"),
        abi.Argument(arg_type="uint64", name="lock_end_time"),
    ]
)

event_increase_lock_amount = Event(
    name="increase_lock_amount",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="locked_amount"),
        abi.Argument(arg_type="uint64", name="lock_end_time"),
        abi.Argument(arg_type="uint64", name="amount_delta"),
    ]
)

event_extend_lock_end_time = Event(
    name="extend_lock_end_time",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="locked_amount"),
        abi.Argument(arg_type="uint64", name="lock_end_time"),
        abi.Argument(arg_type="uint64", name="time_delta"),
    ]
)

event_withdraw = Event(
    name="withdraw",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="amount"),
    ]
)

event_account_power = Event(
    name="account_power",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="bias"),
        abi.Argument(arg_type="uint64", name="timestamp"),
        abi.Argument(arg_type="uint128", name="slope"),
        abi.Argument(arg_type="uint128", name="cumulative_power"),
    ]
)

event_total_power = Event(
    name="total_power",
    args=[
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="bias"),
        abi.Argument(arg_type="uint64", name="timestamp"),
        abi.Argument(arg_type="uint128", name="slope"),
        abi.Argument(arg_type="uint128", name="cumulative_power"),
    ]
)

event_slope_change = Event(
    name="slope_change",
    args=[
        abi.Argument(arg_type="uint64", name="timestamp"),
        abi.Argument(arg_type="uint128", name="slope"),
    ]
)

vault_events = [
    # method calls
    event_init,
    event_create_checkpoints,
    event_create_lock,
    event_increase_lock_amount,
    event_extend_lock_end_time,
    event_withdraw,
    event_del_box,
    event_delete_account_state,
    event_delete_account_power_boxes,
    # boxes
    event_account_power,
    event_total_power,
    event_slope_change,
]

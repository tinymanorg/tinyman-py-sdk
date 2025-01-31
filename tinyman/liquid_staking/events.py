from algosdk import abi

from tinyman.event import Event


user_state_event = Event(
    name="user_state",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="staked_amount"),
        abi.Argument(arg_type="uint64", name="accumulated_rewards_per_unit_at_last_update"),
        abi.Argument(arg_type="uint64", name="accumulated_rewards"),
        abi.Argument(arg_type="uint64", name="timestamp"),
    ]
)


create_application_event = Event(
    name="create_application",
    args=[
        abi.Argument(arg_type="uint64", name="talgo_asset_id"),
        abi.Argument(arg_type="uint64", name="tiny_asset_id"),
        abi.Argument(arg_type="uint64", name="vault_app_id"),
        abi.Argument(arg_type="address", name="manager_address"),
    ]
)


init_event = Event(
    name="init",
    args=[
        abi.Argument(arg_type="uint64", name="stalgo_asset_id")
    ]
)


state_event = Event(
    name="state",
    args=[
        abi.Argument(arg_type="uint64", name="last_update_timestamp"),
        abi.Argument(arg_type="uint64", name="current_reward_rate_per_time"),
        abi.Argument(arg_type="uint64", name="accumulated_rewards_per_unit"),
        abi.Argument(arg_type="uint64", name="total_staked_amount"),
    ]
)


update_user_state_event = Event(
    name="update_user_state",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
    ]
)


set_reward_rate_event = Event(
    name="set_reward_rate",
    args=[
        abi.Argument(arg_type="uint64", name="total_reward_amount"),
        abi.Argument(arg_type="uint64", name="start_timestamp"),
        abi.Argument(arg_type="uint64", name="end_timestamp"),
        abi.Argument(arg_type="uint64", name="current_reward_rate_per_time"),
    ]
)


propose_manager_event = Event(
    name="propose_manager",
    args=[
        abi.Argument(arg_type="address", name="proposed_manager")
    ]
)


accept_manager_event = Event(
    name="accept_manager",
    args=[
        abi.Argument(arg_type="address", name="new_manager")
    ]
)


apply_rate_change_event = Event(
    name="apply_rate_change",
    args=[
        abi.Argument(arg_type="uint64", name="current_reward_rate_per_time"),
    ]
)


increase_stake_event = Event(
    name="increase_stake",
    args=[
        abi.Argument(arg_type="uint64", name="amount"),
    ]
)


decrease_stake_event = Event(
    name="decrease_stake",
    args=[
        abi.Argument(arg_type="uint64", name="amount"),
    ]
)


claim_rewards_event = Event(
    name="claim_rewards",
    args=[
        abi.Argument(arg_type="uint64", name="amount"),
    ]
)


set_tiny_power_threshold_event = Event(
    name="set_tiny_power_threshold",
    args=[
        abi.Argument(arg_type="uint64", name="threshold"),
    ]
)


restaking_events = [
    create_application_event,
    init_event,
    state_event,
    set_reward_rate_event,
    propose_manager_event,
    accept_manager_event,
    set_tiny_power_threshold_event,
    apply_rate_change_event,
    user_state_event,
    update_user_state_event,
    increase_stake_event,
    decrease_stake_event,
    claim_rewards_event
]


rate_update_event = Event(
    name="rate_update",
    args=[
        abi.Argument(arg_type="uint64", name="rate"),
    ]
)


mint_event = Event(
    name="mint",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="algo_amount"),
        abi.Argument(arg_type="uint64", name="talgo_amount"),
    ]
)


burn_event = Event(
    name="burn",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="talgo_amount"),
        abi.Argument(arg_type="uint64", name="algo_amount"),
    ]
)


claim_protocol_rewards_event = Event(
    name="claim_protocol_rewards",
    args=[
        abi.Argument(arg_type="uint64", name="amount")
    ]
)


move_stake_event = Event(
    name="move_stake",
    args=[
        abi.Argument(arg_type="uint64", name="from_index"),
        abi.Argument(arg_type="uint64", name="to_index"),
        abi.Argument(arg_type="uint64", name="amount")
    ]
)


set_node_manager_event = Event(
    name="set_node_manager",
    args=[
        abi.Argument(arg_type="uint64", name="node_index"),
        abi.Argument(arg_type="address", name="new_node_manager")
    ]
)


set_stake_manager_event = Event(
    name="set_stake_manager",
    args=[
        abi.Argument(arg_type="address", name="new_stake_manager")
    ]
)


set_fee_collector_event = Event(
    name="set_fee_collector",
    args=[
        abi.Argument(arg_type="address", name="new_fee_collector")
    ]
)


set_protocol_fee_event = Event(
    name="set_protocol_fee",
    args=[
        abi.Argument(arg_type="uint64", name="fee_rate")
    ]
)


set_max_account_balance_event = Event(
    name="set_max_account_balance",
    args=[
        abi.Argument(arg_type="uint64", name="max_amount")
    ]
)


change_online_status_event = Event(
    name="change_online_status",
    args=[
        abi.Argument(arg_type="uint64", name="node_index")
    ]
)


talgo_events = [
    rate_update_event,
    mint_event,
    burn_event,
    claim_protocol_rewards_event,
    move_stake_event,
    propose_manager_event,
    accept_manager_event,
    set_node_manager_event,
    set_stake_manager_event,
    set_fee_collector_event,
    set_protocol_fee_event,
    set_max_account_balance_event,
    change_online_status_event,
]

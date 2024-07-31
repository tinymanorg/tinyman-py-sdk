from algosdk import abi

from tinyman.governance.event import Event


event_init = Event(
    name="init",
    args=[
        abi.Argument(arg_type="uint64", name="first_period_timestamp"),
        abi.Argument(arg_type="uint64", name="reward_amount"),
    ]
)

event_set_reward_amount = Event(
    name="set_reward_amount",
    args=[
        abi.Argument(arg_type="uint64", name="timestamp"),
        abi.Argument(arg_type="uint64", name="reward_amount"),
    ]
)

event_create_reward_period = Event(
    name="create_reward_period",
    args=[
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="total_reward_amount"),
        abi.Argument(arg_type="uint128", name="total_cumulative_power_delta"),
    ]
)

event_claim_rewards = Event(
    name="claim_rewards",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="total_reward_amount"),
        abi.Argument(arg_type="uint64", name="period_index_start"),
        abi.Argument(arg_type="uint64", name="period_count"),
        abi.Argument(arg_type="uint64[]", name="reward_amounts"),
    ]
)

event_set_manager = Event(
    name="set_manager",
    args=[
        abi.Argument(arg_type="address", name="manager"),
    ]
)

event_set_rewards_manager = Event(
    name="set_rewards_manager",
    args=[
        abi.Argument(arg_type="address", name="rewards_manager"),
    ]
)

event_reward_period = Event(
    name="reward_period",
    args=[
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="total_reward_amount"),
        abi.Argument(arg_type="uint128", name="total_cumulative_power_delta"),
    ]
)

event_reward_history = Event(
    name="reward_history",
    args=[
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="timestamp"),
        abi.Argument(arg_type="uint64", name="reward_amount"),
    ]
)


rewards_events = [
    # method calls
    event_init,
    event_set_reward_amount,
    event_claim_rewards,
    event_create_reward_period,
    event_set_manager,
    event_set_rewards_manager,
    # boxes
    event_reward_period,
    event_reward_history,
]

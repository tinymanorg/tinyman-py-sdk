from algosdk import abi

from tinyman.governance.event import Event


event_proposal = Event(
    name="proposal",
    args=[
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
        abi.Argument(arg_type="uint64", name="index"),
        abi.Argument(arg_type="uint64", name="creation_timestamp"),
        abi.Argument(arg_type="uint64", name="voting_start_timestamp"),
        abi.Argument(arg_type="uint64", name="voting_end_timestamp"),
        abi.Argument(arg_type="uint64", name="voting_power"),
        abi.Argument(arg_type="uint64", name="vote_count"),
        abi.Argument(arg_type="bool", name="is_cancelled"),
    ]
)

event_create_proposal = Event(
    name="create_proposal",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
    ]
)

event_cancel_proposal = Event(
    name="cancel_proposal",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
    ]
)

event_vote = Event(
    name="vote",
    args=[
        abi.Argument(arg_type="uint64", name="asset_id"),
        abi.Argument(arg_type="uint64", name="voting_power"),
        abi.Argument(arg_type="uint64", name="vote_percentage"),
    ]
)

event_cast_vote = Event(
    name="cast_vote",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
        abi.Argument(arg_type="uint64", name="voting_power"),
    ]
)

event_set_manager = Event(
    name="set_manager",
    args=[
        abi.Argument(arg_type="address", name="manager"),
    ]
)

event_set_proposal_manager = Event(
    name="set_proposal_manager",
    args=[
        abi.Argument(arg_type="address", name="proposal_manager"),
    ]
)

event_set_voting_delay = Event(
    name="set_voting_delay",
    args=[
        abi.Argument(arg_type="uint64", name="voting_delay"),
    ]
)

event_set_voting_duration = Event(
    name="set_voting_duration",
    args=[
        abi.Argument(arg_type="uint64", name="voting_duration"),
    ]
)

staking_voting_events = [
    # method calls
    event_create_proposal,
    event_cancel_proposal,
    event_cast_vote,
    event_set_manager,
    event_set_proposal_manager,
    event_set_voting_delay,
    event_set_voting_duration,
    # boxes
    event_vote,
    event_proposal,
]

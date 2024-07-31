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
        abi.Argument(arg_type="uint64", name="snapshot_total_voting_power"),
        abi.Argument(arg_type="uint64", name="vote_count"),
        abi.Argument(arg_type="uint64", name="quorum_threshold"),
        abi.Argument(arg_type="uint64", name="against_voting_power"),
        abi.Argument(arg_type="uint64", name="for_voting_power"),
        abi.Argument(arg_type="uint64", name="abstain_voting_power"),
        abi.Argument(arg_type="bool", name="is_approved"),
        abi.Argument(arg_type="bool", name="is_cancelled"),
        abi.Argument(arg_type="bool", name="is_executed"),
        abi.Argument(arg_type="bool", name="is_quorum_reached"),
        abi.Argument(arg_type="address", name="proposer_address"),
        abi.Argument(arg_type="byte[34]", name="execution_hash"),
        abi.Argument(arg_type="address", name="executor_address"),
    ]
)

event_approve_proposal = Event(
    name="approve_proposal",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
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

event_execute_proposal = Event(
    name="execute_proposal",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
    ]
)


event_cast_vote = Event(
    name="cast_vote",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="byte[59]", name="proposal_id"),
        abi.Argument(arg_type="uint64", name="vote"),
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


event_set_proposal_threshold = Event(
    name="set_proposal_threshold",
    args=[
        abi.Argument(arg_type="uint64", name="proposal_threshold"),
    ]
)


event_set_proposal_threshold_numerator = Event(
    name="set_proposal_threshold_numerator",
    args=[
        abi.Argument(arg_type="uint64", name="proposal_threshold_numerator"),
    ]
)


event_set_quorum_threshold = Event(
    name="set_quorum_threshold",
    args=[
        abi.Argument(arg_type="uint64", name="quorum_threshold"),
    ]
)

event_disable_approval_requirement = Event(
    name="disable_approval_requirement",
    args=[]
)

proposal_voting_events = [
    # method calls
    event_create_proposal,
    event_approve_proposal,
    event_cancel_proposal,
    event_execute_proposal,
    event_cast_vote,
    event_set_manager,
    event_set_proposal_manager,
    event_set_voting_delay,
    event_set_voting_duration,
    event_set_proposal_threshold,
    event_set_proposal_threshold_numerator,
    event_set_quorum_threshold,
    event_disable_approval_requirement,
    # boxes
    event_proposal,
]

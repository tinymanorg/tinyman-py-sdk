from algosdk import abi

from .event import Event


# Registry Events
entry_event = Event(
    name="entry",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="app_id")
    ]
)

set_order_fee_rate_event = Event(
    name="set_order_fee_rate",
    args=[
        abi.Argument(arg_type="uint64", name="fee_rate")
    ]
)

set_governor_order_fee_rate_event = Event(
    name="set_governor_order_fee_rate",
    args=[
        abi.Argument(arg_type="uint64", name="fee_rate")
    ]
)

set_governor_fee_rate_power_threshold_event = Event(
    name="set_governor_fee_rate_power_threshold",
    args=[
        abi.Argument(arg_type="uint64", name="threshold")
    ]
)

claim_fees_event = Event(
    name="claim_fees",
    args=[
        abi.Argument(arg_type="uint64", name="asset_id"),
        abi.Argument(arg_type="uint64", name="amount")
    ]
)


endorse_event = Event(
    name="endorse",
    args=[
        abi.Argument(arg_type="address", name="user_address")
    ]
)


deendorse_event = Event(
    name="deendorse",
    args=[
        abi.Argument(arg_type="address", name="user_address")
    ]
)


approve_version_event = Event(
    name="approve_version",
    args=[
        abi.Argument(arg_type="uint64", name="version"),
        abi.Argument(arg_type="byte[32]", name="approval_hash")
    ]
)


propose_manager_event = Event(
    name="propose_manager",
    args=[
        abi.Argument(arg_type="address", name="proposed_manager"),
    ]
)


accept_manager_event = Event(
    name="accept_manager",
    args=[
        abi.Argument(arg_type="address", name="new_manager"),
    ]
)


trigger_order_fields = [
    abi.Argument(arg_type="uint64", name="asset_id"),
    abi.Argument(arg_type="uint64", name="amount"),
    abi.Argument(arg_type="uint64", name="target_asset_id"),
    abi.Argument(arg_type="uint64", name="target_amount"),
    abi.Argument(arg_type="uint64", name="filled_amount"),
    abi.Argument(arg_type="uint64", name="collected_target_amount"),
    abi.Argument(arg_type="uint64", name="is_partial_allowed"),
    abi.Argument(arg_type="uint64", name="fee_rate"),
    abi.Argument(arg_type="uint64", name="creation_timestamp"),
    abi.Argument(arg_type="uint64", name="expiration_timestamp")
]

recurring_order_fields = [
    abi.Argument(arg_type="uint64", name="asset_id"),
    abi.Argument(arg_type="uint64", name="amount"),
    abi.Argument(arg_type="uint64", name="target_asset_id"),
    abi.Argument(arg_type="uint64", name="collected_target_amount"),
    abi.Argument(arg_type="uint64", name="min_target_amount"),
    abi.Argument(arg_type="uint64", name="max_target_amount"),
    abi.Argument(arg_type="uint64", name="remaining_recurrences"),
    abi.Argument(arg_type="uint64", name="interval"),
    abi.Argument(arg_type="uint64", name="fee_rate"),
    abi.Argument(arg_type="uint64", name="last_fill_timestamp"),
    abi.Argument(arg_type="uint64", name="creation_timestamp")
]


registry_update_ordering_application_event = Event(
    name="update_ordering_application",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="version"),
    ]
)


registry_put_trigger_order_event = Event(
    name="put_trigger_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + trigger_order_fields
)


registry_update_trigger_order_event = Event(
    name="update_trigger_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + trigger_order_fields
)


registry_cancel_trigger_order_event = Event(
    name="cancel_trigger_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


registry_put_recurring_order_event = Event(
    name="put_recurring_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + recurring_order_fields
)


registry_update_recurring_order_event = Event(
    name="update_recurring_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + recurring_order_fields
)


registry_cancel_recurring_order_event = Event(
    name="cancel_recurring_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_app_id"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


# Order Events
update_application_event = Event(
    name="update_application",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="version"),
    ]
)


trigger_order_event = Event(
    name="trigger_order",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + trigger_order_fields
)


put_trigger_order_event = Event(
    name="put_trigger_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


cancel_trigger_order_event = Event(
    name="cancel_trigger_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


start_execute_trigger_order_event = Event(
    name="start_execute_trigger_order",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="order_id"),
        abi.Argument(arg_type="address", name="filler_address"),
    ]
)


end_execute_trigger_order_event = Event(
    name="end_execute_trigger_order",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="order_id"),
        abi.Argument(arg_type="address", name="filler_address"),
        abi.Argument(arg_type="uint64", name="fill_amount"),
        abi.Argument(arg_type="uint64", name="bought_amount"),
    ]
)


collect_event = Event(
    name="collect",
    args=[
        abi.Argument(arg_type="uint64", name="order_id"),
        abi.Argument(arg_type="uint64", name="collected_target_amount")
    ]
)


# Recurring Order Events
recurring_order_event = Event(
    name="recurring_order",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="order_id"),
    ] + recurring_order_fields
)


put_recurring_order_event = Event(
    name="put_recurring_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


cancel_recurring_order_event = Event(
    name="cancel_recurring_order",
    args=[
        abi.Argument(arg_type="uint64", name="order_id"),
    ]
)


execute_recurring_order_event = Event(
    name="execute_recurring_order",
    args=[
        abi.Argument(arg_type="address", name="user_address"),
        abi.Argument(arg_type="uint64", name="order_id"),
        abi.Argument(arg_type="address", name="filler_address"),
        abi.Argument(arg_type="uint64", name="fill_amount"),
        abi.Argument(arg_type="uint64", name="bought_amount"),
    ]
)


registry_events = [
    set_order_fee_rate_event,
    set_governor_order_fee_rate_event,
    set_governor_fee_rate_power_threshold_event,
    claim_fees_event,
    endorse_event,
    deendorse_event,
    approve_version_event,
    propose_manager_event,
    accept_manager_event,
    entry_event,
    registry_update_ordering_application_event,
    registry_put_trigger_order_event,
    registry_update_trigger_order_event,
    registry_cancel_trigger_order_event,
    registry_put_recurring_order_event,
    registry_update_recurring_order_event,
    registry_cancel_recurring_order_event,
]


ordering_events = [
    update_application_event,
    trigger_order_event,
    put_trigger_order_event,
    cancel_trigger_order_event,
    start_execute_trigger_order_event,
    end_execute_trigger_order_event,
    collect_event,
    recurring_order_event,
    put_recurring_order_event,
    cancel_recurring_order_event,
    execute_recurring_order_event,
]
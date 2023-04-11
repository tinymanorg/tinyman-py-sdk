TESTNET_SWAP_ROUTER_APP_ID_V1 = 184778019
MAINNET_SWAP_ROUTER_APP_ID_V1 = 1071281873  # TODO: temp app for testing.

FIXED_INPUT_SWAP_TYPE = "fixed-input"
FIXED_OUTPUT_SWAP_TYPE = "fixed-output"

SWAP_APP_ARGUMENT = b"swap"
FIXED_INPUT_APP_ARGUMENT = b"fixed-input"
FIXED_OUTPUT_APP_ARGUMENT = b"fixed-output"
ASSET_OPT_IN_APP_ARGUMENT = b"asset_opt_in"
CLAIM_EXTRA_APP_ARGUMENT = b"claim_extra"
SET_MANAGER_APP_ARGUMENT = b"set_manager"
SET_EXTRA_COLLECTOR_APP_ARGUMENT = b"set_extra_collector"

# Event Log Selectors
SWAP_EVENT_LOG_SELECTOR = b"\x81b\xda\x9e"  # "swap(uint64,uint64,uint64,uint64)"

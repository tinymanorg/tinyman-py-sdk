import requests
from algosdk import transaction

# Order App Globals & Commons with Registry
REGISTRY_APP_ID_KEY = b"registry_app_id"
REGISTRY_APP_ACCOUNT_ADDRESS_KEY = b"registry_app_account_address"
VAULT_APP_ID_KEY = b"vault_app_id"
ROUTER_APP_ID_KEY = b"router_app_id"
ORDER_FEE_RATE_KEY = b"order_fee_rate"
GOVERNOR_ORDER_FEE_RATE_KEY = b"governor_order_fee_rate"
GOVERNOR_FEE_RATE_POWER_THRESHOLD = b"governor_fee_rate_power_threshold"

USER_ADDRESS_KEY = b"user_address"
TOTAL_ORDER_COUNT_KEY = b"order_count"
PROPOSED_MANAGER_KEY = b"proposed_manager"
MANAGER_KEY = b"manager"
VERSION_KEY = b"version"

# Registry App Globals
ENTRY_COUNT_KEY = b"entry_count"

# Registry App Locals
IS_ENDORSED_KEY = b"is_endorsed"

# App Creation Config
order_approval_program = requests.get("https://raw.githubusercontent.com/tinymanorg/tinyman-order-protocol/refs/tags/v5/contracts/order/build/order_approval.teal.tok").content
order_clear_state_program = requests.get("https://raw.githubusercontent.com/tinymanorg/tinyman-order-protocol/refs/tags/v5/contracts/order/build/order_clear_state.teal.tok").content
order_app_global_schema = transaction.StateSchema(num_uints=16, num_byte_slices=16)
order_app_local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)
order_app_extra_pages = 3

# App Ids
TESTNET_ORDERING_REGISTRY_APP_ID = 739800082
MAINNET_ORDERING_REGISTRY_APP_ID = 3019195131

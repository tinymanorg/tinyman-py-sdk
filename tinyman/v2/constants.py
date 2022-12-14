from algosdk.logic import get_application_address

BOOTSTRAP_APP_ARGUMENT = b"bootstrap"
ADD_LIQUIDITY_APP_ARGUMENT = b"add_liquidity"
ADD_INITIAL_LIQUIDITY_APP_ARGUMENT = b"add_initial_liquidity"
REMOVE_LIQUIDITY_APP_ARGUMENT = b"remove_liquidity"
SWAP_APP_ARGUMENT = b"swap"
FLASH_LOAN_APP_ARGUMENT = b"flash_loan"
VERIFY_FLASH_LOAN_APP_ARGUMENT = b"verify_flash_loan"
FLASH_SWAP_APP_ARGUMENT = b"flash_swap"
VERIFY_FLASH_SWAP_APP_ARGUMENT = b"verify_flash_swap"
CLAIM_FEES_APP_ARGUMENT = b"claim_fees"
CLAIM_EXTRA_APP_ARGUMENT = b"claim_extra"
SET_FEE_APP_ARGUMENT = b"set_fee"
SET_FEE_COLLECTOR_APP_ARGUMENT = b"set_fee_collector"
SET_FEE_SETTER_APP_ARGUMENT = b"set_fee_setter"
SET_FEE_MANAGER_APP_ARGUMENT = b"set_fee_manager"

FIXED_INPUT_APP_ARGUMENT = b"fixed-input"
FIXED_OUTPUT_APP_ARGUMENT = b"fixed-output"

ADD_LIQUIDITY_FLEXIBLE_MODE_APP_ARGUMENT = b"flexible"
ADD_LIQUIDITY_SINGLE_MODE_APP_ARGUMENT = b"single"


TESTNET_VALIDATOR_APP_ID_V2 = 148607000
MAINNET_VALIDATOR_APP_ID_V2 = None

TESTNET_VALIDATOR_APP_ID = TESTNET_VALIDATOR_APP_ID_V2
MAINNET_VALIDATOR_APP_ID = None

TESTNET_VALIDATOR_APP_ADDRESS = get_application_address(TESTNET_VALIDATOR_APP_ID)
# MAINNET_VALIDATOR_APP__ADDRESS = get_application_address(MAINNET_VALIDATOR_APP_ID)

LOCKED_POOL_TOKENS = 1000
ASSET_MIN_TOTAL = 1000000

# State
APP_LOCAL_INTS = 12
APP_LOCAL_BYTES = 2
APP_GLOBAL_INTS = 0
APP_GLOBAL_BYTES = 3

# 100,000 Algo
# + 100,000 ASA 1
# + 100,000 ASA 2
# + 100,000 Pool Token
# + 542,500 App Optin (100000 + (25000+3500)*12 + (25000+25000)*2)
MIN_POOL_BALANCE_ASA_ALGO_PAIR = 300_000 + (
    100_000 + (25_000 + 3_500) * APP_LOCAL_INTS + (25_000 + 25_000) * APP_LOCAL_BYTES
)
MIN_POOL_BALANCE_ASA_ASA_PAIR = MIN_POOL_BALANCE_ASA_ALGO_PAIR + 100_000

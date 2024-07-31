# Global states
from tinyman.constants import MINIMUM_BALANCE_REQUIREMENT_PER_BOX, MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE

FIRST_PERIOD_TIMESTAMP = b'first_period_timestamp'
REWARD_HISTORY_COUNT_KEY = b'reward_history_count'
REWARD_PERIOD_COUNT_KEY = b'reward_period_count'
MANAGER_KEY = b'manager'
REWARDS_MANAGER_KEY = b'rewards_manager'

# Boxes
REWARD_PERIOD_BOX_PREFIX = b'rp'
REWARD_HISTORY_BOX_PREFIX = b'rh'
REWARD_CLAIM_SHEET_BOX_PREFIX = b'c'

REWARD_CLAIM_SHEET_BOX_SIZE = 1012

REWARD_HISTORY_SIZE = 16
REWARD_HISTORY_BOX_SIZE = 256
REWARD_HISTORY_BOX_ARRAY_LEN = 16

REWARD_PERIOD_SIZE = 24
REWARD_PERIOD_BOX_SIZE = 1008
REWARD_PERIOD_BOX_ARRAY_LEN = 42

REWARD_CLAIM_SHEET_BOX_COST = MINIMUM_BALANCE_REQUIREMENT_PER_BOX + MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE * (41 + REWARD_CLAIM_SHEET_BOX_SIZE)
REWARD_PERIOD_BOX_COST = MINIMUM_BALANCE_REQUIREMENT_PER_BOX + MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE * (10 + REWARD_PERIOD_BOX_SIZE)
REWARD_HISTORY_BOX_COST = MINIMUM_BALANCE_REQUIREMENT_PER_BOX + MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE * (10 + REWARD_HISTORY_BOX_SIZE)

# 100_000 Default
# 100_000 Opt-in
# Box
REWARDS_APP_MINIMUM_BALANCE_REQUIREMENT = 200_000 + REWARD_HISTORY_BOX_COST

INIT_APP_ARGUMENT = b"init"
SET_REWARD_AMOUNT_APP_ARGUMENT = b"set_reward_amount"
CREATE_REWARD_PERIOD_APP_ARGUMENT = b"create_reward_period"
CLAIM_REWARDS_APP_ARGUMENT = b"claim_rewards"
SET_REWARDS_MANAGER_APP_ARGUMENT = b"set_rewards_manager"

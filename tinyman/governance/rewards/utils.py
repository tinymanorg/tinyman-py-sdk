from tinyman.governance.rewards.storage import RewardPeriod


def calculate_reward_amount(account_cumulative_power_delta: int, reward_period: RewardPeriod):
    return reward_period.total_reward_amount * account_cumulative_power_delta // reward_period.total_cumulative_power_delta


def group_adjacent_period_indexes(indexes: list[int]) -> list[list[int]]:
    if not indexes:  # Handle empty list
        return []

    grouped = []
    current_group = [indexes[0]]

    for i in range(1, len(indexes)):
        # Check if the current number is adjacent to the previous number
        if indexes[i] - indexes[i - 1] == 1:
            current_group.append(indexes[i])
        else:
            grouped.append(current_group)
            current_group = [indexes[i]]

    # Append the last group after exiting the loop
    grouped.append(current_group)

    return grouped

import math

from tinyman.utils import calculate_price_impact
from tinyman.v2.constants import LOCKED_POOL_TOKENS
from tinyman.exceptions import InsufficientReserves, LowSwapAmountError


def calculate_protocol_fee_amount(
    total_fee_amount: int, protocol_fee_ratio: int
) -> int:
    protocol_fee_amount = total_fee_amount // protocol_fee_ratio
    return protocol_fee_amount


def calculate_poolers_fee_amount(total_fee_amount: int, protocol_fee_ratio: int) -> int:
    protocol_fee_amount = calculate_protocol_fee_amount(
        total_fee_amount, protocol_fee_ratio
    )
    poolers_fee_amount = total_fee_amount - protocol_fee_amount
    return poolers_fee_amount


def calculate_fixed_input_fee_amount(input_amount: int, total_fee_share: int) -> int:
    total_fee_amount = (input_amount * total_fee_share) // 10_000
    return total_fee_amount


def calculate_fixed_output_fee_amount(swap_amount: int, total_fee_share: int) -> int:
    input_amount = (swap_amount * 10_000) // (10_000 - total_fee_share)
    total_fee_amount = input_amount - swap_amount
    return total_fee_amount


def calculate_internal_swap_fee_amount(swap_amount: int, total_fee_share: int) -> int:
    total_fee_amount = int((swap_amount * total_fee_share) / (10_000 - total_fee_share))
    return total_fee_amount


def calculate_flash_loan_payment_amount(loan_amount: int, total_fee_share: int) -> int:
    total_fee_amount = calculate_fixed_input_fee_amount(loan_amount, total_fee_share)
    payment_amount = loan_amount + total_fee_amount
    return payment_amount


def calculate_flash_swap_asset_2_payment_amount(
    asset_1_reserves: int,
    asset_2_reserves: int,
    total_fee_share: int,
    protocol_fee_ratio: int,
    asset_1_loan_amount: int,
    asset_2_loan_amount: int,
    asset_1_payment_amount: int,
) -> int:
    k = asset_1_reserves * asset_2_reserves
    asset_1_total_fee_amount = calculate_fixed_input_fee_amount(
        asset_1_payment_amount, total_fee_share
    )
    asset_1_protocol_fee_amount = calculate_protocol_fee_amount(
        asset_1_total_fee_amount, protocol_fee_ratio
    )
    asset_1_poolers_fee_amount = calculate_poolers_fee_amount(
        asset_1_total_fee_amount, protocol_fee_ratio
    )

    final_asset_1_reserves = (asset_1_reserves - asset_1_loan_amount) + (
        asset_1_payment_amount - asset_1_protocol_fee_amount
    )
    final_asset_1_reserves_without_poolers_fee = (
        final_asset_1_reserves - asset_1_poolers_fee_amount
    )
    minimum_final_asset_2_reserves_without_poolers_fee = (
        k / final_asset_1_reserves_without_poolers_fee
    )
    minimum_asset_2_payment_amount_without_poolers_fee = (
        minimum_final_asset_2_reserves_without_poolers_fee
        - (asset_2_reserves - asset_2_loan_amount)
    )
    minimum_asset_2_payment_amount = math.ceil(
        minimum_asset_2_payment_amount_without_poolers_fee
        * 10_000
        / (10_000 - total_fee_share)
    )
    return minimum_asset_2_payment_amount


def calculate_flash_swap_asset_1_payment_amount(
    asset_1_reserves: int,
    asset_2_reserves: int,
    total_fee_share: int,
    protocol_fee_ratio: int,
    asset_1_loan_amount: int,
    asset_2_loan_amount: int,
    asset_2_payment_amount: int,
) -> int:
    k = asset_1_reserves * asset_2_reserves
    asset_2_total_fee_amount = calculate_fixed_input_fee_amount(
        asset_2_payment_amount, total_fee_share
    )
    asset_2_protocol_fee_amount = calculate_protocol_fee_amount(
        asset_2_total_fee_amount, protocol_fee_ratio
    )
    asset_2_poolers_fee_amount = calculate_poolers_fee_amount(
        asset_2_total_fee_amount, protocol_fee_ratio
    )

    final_asset_2_reserves = (asset_2_reserves - asset_2_loan_amount) + (
        asset_2_payment_amount - asset_2_protocol_fee_amount
    )
    final_asset_2_reserves_without_poolers_fee = (
        final_asset_2_reserves - asset_2_poolers_fee_amount
    )
    minimum_final_asset_1_reserves_without_poolers_fee = (
        k / final_asset_2_reserves_without_poolers_fee
    )
    minimum_asset_1_payment_amount_without_poolers_fee = (
        minimum_final_asset_1_reserves_without_poolers_fee
        - (asset_1_reserves - asset_1_loan_amount)
    )

    minimum_asset_1_payment_amount = math.ceil(
        minimum_asset_1_payment_amount_without_poolers_fee
        * 10_000
        / (10_000 - total_fee_share)
    )
    return minimum_asset_1_payment_amount


def calculate_initial_add_liquidity(asset_1_amount: int, asset_2_amount: int) -> int:
    assert bool(asset_1_amount) and bool(
        asset_2_amount
    ), "Both assets are required for the initial add liquidity"

    pool_token_asset_amount = (
        int(math.sqrt(asset_1_amount * asset_2_amount)) - LOCKED_POOL_TOKENS
    )
    return pool_token_asset_amount


def calculate_remove_liquidity_output_amounts(
    pool_token_asset_amount: int,
    asset_1_reserves: int,
    asset_2_reserves: int,
    issued_pool_tokens: int,
) -> (int, int):
    if issued_pool_tokens > (pool_token_asset_amount + LOCKED_POOL_TOKENS):
        asset_1_output_amount = (
            pool_token_asset_amount * asset_1_reserves / issued_pool_tokens
        )
        asset_2_output_amount = (
            pool_token_asset_amount * asset_2_reserves / issued_pool_tokens
        )
    else:
        asset_1_output_amount = asset_1_reserves
        asset_2_output_amount = asset_2_reserves

    return int(asset_1_output_amount), int(asset_2_output_amount)


def calculate_subsequent_add_liquidity(
    asset_1_reserves: int,
    asset_2_reserves: int,
    issued_pool_tokens: int,
    total_fee_share: int,
    asset_1_amount: int,
    asset_2_amount: int,
) -> (int, bool, int, int, int, float):
    assert asset_1_reserves and asset_2_reserves and issued_pool_tokens

    old_k = asset_1_reserves * asset_2_reserves
    new_asset_1_reserves = asset_1_reserves + asset_1_amount
    new_asset_2_reserves = asset_2_reserves + asset_2_amount
    new_k = new_asset_1_reserves * new_asset_2_reserves
    new_issued_pool_tokens = int(
        math.sqrt(int((new_k * (issued_pool_tokens**2)) / old_k))
    )

    pool_token_asset_amount = new_issued_pool_tokens - issued_pool_tokens
    calculated_asset_1_amount = int(
        (pool_token_asset_amount * new_asset_1_reserves) / new_issued_pool_tokens
    )
    calculated_asset_2_amount = int(
        (pool_token_asset_amount * new_asset_2_reserves) / new_issued_pool_tokens
    )

    asset_1_swap_amount = asset_1_amount - calculated_asset_1_amount
    asset_2_swap_amount = asset_2_amount - calculated_asset_2_amount

    if asset_1_swap_amount > asset_2_swap_amount:
        swap_in_amount_without_fee = asset_1_swap_amount
        swap_out_amount = -min(asset_2_swap_amount, 0)
        swap_from_asset_1_to_asset_2 = True

        swap_total_fee_amount = calculate_internal_swap_fee_amount(
            swap_in_amount_without_fee,
            total_fee_share,
        )
        fee_as_pool_tokens = int(
            swap_total_fee_amount * new_issued_pool_tokens / (new_asset_1_reserves * 2)
        )
        swap_in_amount = swap_in_amount_without_fee + swap_total_fee_amount
        pool_token_asset_amount = pool_token_asset_amount - fee_as_pool_tokens
    else:
        swap_in_amount_without_fee = asset_2_swap_amount
        swap_out_amount = -min(asset_1_swap_amount, 0)
        swap_from_asset_1_to_asset_2 = False

        swap_total_fee_amount = calculate_internal_swap_fee_amount(
            swap_in_amount_without_fee,
            total_fee_share,
        )
        fee_as_pool_tokens = int(
            swap_total_fee_amount * new_issued_pool_tokens / (new_asset_2_reserves * 2)
        )
        swap_in_amount = swap_in_amount_without_fee + swap_total_fee_amount
        pool_token_asset_amount = pool_token_asset_amount - fee_as_pool_tokens

    swap_price_impact = calculate_price_impact(
        input_supply=asset_1_reserves
        if swap_from_asset_1_to_asset_2
        else asset_2_reserves,
        output_supply=asset_2_reserves
        if swap_from_asset_1_to_asset_2
        else asset_1_reserves,
        swap_input_amount=swap_in_amount,
        swap_output_amount=swap_out_amount,
    )
    return (
        pool_token_asset_amount,
        swap_from_asset_1_to_asset_2,
        swap_in_amount,
        swap_out_amount,
        swap_total_fee_amount,
        swap_price_impact,
    )


def calculate_output_amount_of_fixed_input_swap(
    input_supply: int, output_supply: int, swap_amount: int
) -> int:
    k = input_supply * output_supply
    output_amount = output_supply - int(k / (input_supply + swap_amount))

    # On-chain app raises an error if output_amount is less than zero.
    output_amount = max(output_amount, 0)
    return output_amount


def calculate_swap_amount_of_fixed_output_swap(
    input_supply: int, output_supply: int, output_amount: int
) -> int:
    assert output_supply > output_amount

    k = input_supply * output_supply
    swap_amount = int(k / (output_supply - output_amount)) - input_supply
    swap_amount += 1
    return swap_amount


def calculate_fixed_input_swap(
    input_supply: int, output_supply: int, swap_input_amount: int, total_fee_share: int
) -> (int, int, int, float):
    if not swap_input_amount:
        raise LowSwapAmountError()

    total_fee_amount = calculate_fixed_input_fee_amount(
        input_amount=swap_input_amount, total_fee_share=total_fee_share
    )
    swap_amount = swap_input_amount - total_fee_amount
    swap_output_amount = calculate_output_amount_of_fixed_input_swap(
        input_supply, output_supply, swap_amount
    )

    price_impact = calculate_price_impact(
        input_supply=input_supply,
        output_supply=output_supply,
        swap_input_amount=swap_input_amount,
        swap_output_amount=swap_output_amount,
    )
    return swap_output_amount, total_fee_amount, price_impact


def calculate_fixed_output_swap(
    input_supply: int, output_supply: int, swap_output_amount: int, total_fee_share: int
) -> (int, int, float):
    if output_supply <= swap_output_amount:
        raise InsufficientReserves()

    swap_amount = calculate_swap_amount_of_fixed_output_swap(
        input_supply, output_supply, swap_output_amount
    )
    total_fee_amount = calculate_fixed_output_fee_amount(
        swap_amount=swap_amount, total_fee_share=total_fee_share
    )
    swap_input_amount = swap_amount + total_fee_amount

    price_impact = calculate_price_impact(
        input_supply=input_supply,
        output_supply=output_supply,
        swap_input_amount=swap_input_amount,
        swap_output_amount=swap_output_amount,
    )
    return swap_input_amount, total_fee_amount, price_impact

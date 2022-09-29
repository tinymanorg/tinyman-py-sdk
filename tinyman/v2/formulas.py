import math

from tinyman.assets import AssetAmount
from tinyman.utils import calculate_price_impact
from tinyman.v2.constants import LOCKED_POOL_TOKENS
from tinyman.v2.quotes import InternalSwapQuote


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
    total_fee_amount = (input_amount * total_fee_share) // 10000
    return total_fee_amount


def calculate_fixed_output_fee_amounts(swap_amount: int, total_fee_share: int) -> int:
    input_amount = (swap_amount * 10000) // (10000 - total_fee_share)
    total_fee_amount = input_amount - swap_amount
    return total_fee_amount


def get_internal_swap_fee_amount(swap_amount, total_fee_share) -> int:
    total_fee_amount = int((swap_amount * total_fee_share) / (10_000 - total_fee_share))
    return total_fee_amount


def get_initial_add_liquidity(asset_1_amount, asset_2_amount) -> int:
    assert (
        not asset_1_amount or not asset_2_amount
    ), "Both assets are required for the initial add liquidity"

    pool_token_asset_amount = (
        int(math.sqrt(asset_1_amount * asset_2_amount)) - LOCKED_POOL_TOKENS
    )
    return pool_token_asset_amount


def calculate_remove_liquidity_output_amounts(
    pool_token_asset_amount, asset_1_reserves, asset_2_reserves, issued_pool_tokens
) -> (int, int):
    asset_1_output_amount = int(
        (pool_token_asset_amount * asset_1_reserves) / issued_pool_tokens
    )
    asset_2_output_amount = int(
        (pool_token_asset_amount * asset_2_reserves) / issued_pool_tokens
    )
    return asset_1_output_amount, asset_2_output_amount


def get_subsequent_add_liquidity(pool, asset_1_amount, asset_2_amount):
    # TODO: Remove pool input and don't return quote here.
    old_k = pool.asset_1_reserves * pool.asset_2_reserves
    new_asset_1_reserves = pool.asset_1_reserves + asset_1_amount
    new_asset_2_reserves = pool.asset_2_reserves + asset_2_amount
    new_k = new_asset_1_reserves * new_asset_2_reserves
    new_issued_pool_tokens = int(
        math.sqrt(int((new_k * (pool.issued_pool_tokens**2)) / old_k))
    )

    pool_token_asset_amount = new_issued_pool_tokens - pool.issued_pool_tokens
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
        swap_in_asset = pool.asset_1
        swap_out_asset = pool.asset_2

        total_fee_amount = get_internal_swap_fee_amount(
            swap_in_amount_without_fee,
            pool.total_fee_share,
        )
        fee_as_pool_tokens = int(
            total_fee_amount * new_issued_pool_tokens / (new_asset_1_reserves * 2)
        )
        swap_in_amount = swap_in_amount_without_fee + total_fee_amount
        pool_token_asset_amount = pool_token_asset_amount - fee_as_pool_tokens
    else:
        swap_in_amount_without_fee = asset_2_swap_amount
        swap_out_amount = -min(asset_1_swap_amount, 0)
        swap_in_asset = pool.asset_2
        swap_out_asset = pool.asset_1

        total_fee_amount = get_internal_swap_fee_amount(
            swap_in_amount_without_fee,
            pool.total_fee_share,
        )
        fee_as_pool_tokens = int(
            total_fee_amount * new_issued_pool_tokens / (new_asset_2_reserves * 2)
        )
        swap_in_amount = swap_in_amount_without_fee + total_fee_amount
        pool_token_asset_amount = pool_token_asset_amount - fee_as_pool_tokens

    price_impact = calculate_price_impact(
        input_supply=pool.asset_1_reserves
        if swap_in_asset == pool.asset_1
        else pool.asset_2_reserves,
        output_supply=pool.asset_1_reserves
        if swap_out_asset == pool.asset_1
        else pool.asset_2_reserves,
        swap_input_amount=swap_in_amount,
        swap_output_amount=swap_out_amount,
    )

    internal_swap_quote = InternalSwapQuote(
        amount_in=AssetAmount(swap_in_asset, swap_in_amount),
        amount_out=AssetAmount(swap_out_asset, swap_out_amount),
        swap_fees=AssetAmount(swap_in_asset, int(total_fee_amount)),
        price_impact=price_impact,
    )

    return pool_token_asset_amount, internal_swap_quote


def calculate_output_amount_of_fixed_input_swap(
    input_supply: int, output_supply: int, swap_amount: int
) -> int:
    k = input_supply * output_supply
    output_amount = output_supply - int(k / (input_supply + swap_amount))
    output_amount -= 1
    return output_amount


def calculate_swap_amount_of_fixed_output_swap(
    input_supply: int, output_supply: int, output_amount: int
) -> int:
    k = input_supply * output_supply
    swap_amount = int(k / (output_supply - output_amount)) - input_supply
    swap_amount += 1
    return swap_amount


def calculate_fixed_input_swap(
    input_supply: int, output_supply: int, swap_input_amount: int, total_fee_share: int
) -> (int, int, int, float):
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
):
    swap_amount = calculate_swap_amount_of_fixed_output_swap(
        input_supply, output_supply, swap_output_amount
    )
    total_fee_amount = calculate_fixed_output_fee_amounts(
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

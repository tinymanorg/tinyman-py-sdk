import math
from dataclasses import dataclass
from typing import Optional
from typing import Union

from tinyman.assets import Asset, AssetAmount
from tinyman.compat import SuggestedParams
from tinyman.exceptions import PoolHasNoLiquidity, InsufficientReserves
from tinyman.utils import TransactionGroup
from tinyman.v1.pools import Pool as TinymanV1Pool
from tinyman.v1.pools import SwapQuote as TinymanV1SwapQuote
from tinyman.v2.pools import Pool as TinymanV2Pool
from tinyman.v2.quotes import SwapQuote as TinymanV2SwapQuote


@dataclass
class Route:
    asset_in: Asset
    asset_out: Asset
    pools: Union[list[TinymanV2Pool], list[TinymanV1Pool]]

    def __str__(self):
        return "Route: " + " -> ".join(f"{pool}" for pool in self.pools)

    def get_fixed_input_quotes(self, amount_in: int, slippage: float = 0.05):
        quotes = []
        assert self.pools

        current_asset_in_amount = AssetAmount(asset=self.asset_in, amount=amount_in)

        for pool in self.pools:
            quote = pool.fetch_fixed_input_swap_quote(
                amount_in=current_asset_in_amount,
                slippage=slippage,
                refresh=False,
            )

            quotes.append(quote)
            current_asset_in_amount = quote.amount_out

        last_quote = quotes[-1]
        assert last_quote.amount_out.asset.id == self.asset_out.id
        return quotes

    def get_fixed_input_last_quote(self, amount_in: int, slippage: float = 0.05):
        try:
            quotes = self.get_fixed_input_quotes(amount_in=amount_in, slippage=slippage)
        except (InsufficientReserves, PoolHasNoLiquidity):
            return None

        last_quote = quotes[-1]
        return last_quote

    def get_fixed_output_quotes(self, amount_out: int, slippage: float = 0.05):
        quotes = []
        assert self.pools

        current_asset_out_amount = AssetAmount(asset=self.asset_out, amount=amount_out)

        for pool in self.pools[::-1]:
            quote = pool.fetch_fixed_output_swap_quote(
                amount_out=current_asset_out_amount,
                slippage=slippage,
                refresh=False,
            )

            quotes.append(quote)
            current_asset_out_amount = quote.amount_in

        quotes.reverse()
        first_quote = quotes[0]
        assert first_quote.amount_in.asset.id == self.asset_in.id
        return quotes

    def get_fixed_output_first_quote(self, amount_out: int, slippage: float = 0.05):
        try:
            quotes = self.get_fixed_output_quotes(
                amount_out=amount_out, slippage=slippage
            )
        except (InsufficientReserves, PoolHasNoLiquidity):
            return None

        first_quote = quotes[0]
        return first_quote

    def prepare_swap_transactions_from_quotes(
        self,
        quotes: list[Union[TinymanV2SwapQuote, TinymanV1SwapQuote]],
        user_address: Optional[str] = None,
        suggested_params: Optional[SuggestedParams] = None,
    ) -> TransactionGroup:
        from tinyman.swap_router.swap_router import prepare_swap_router_transactions

        quote_count = len(quotes)
        if quote_count == 1:
            pool = self.pools[0]
            quote = quotes[0]

            if isinstance(pool, TinymanV1Pool) and isinstance(
                quote, TinymanV1SwapQuote
            ):
                txn_group = pool.prepare_swap_transactions_from_quote(
                    quote=quote,
                    swapper_address=user_address,
                    # suggested_params=suggested_params,
                )
                return txn_group

            elif isinstance(pool, TinymanV2Pool) and isinstance(
                quote, TinymanV2SwapQuote
            ):
                txn_group = pool.prepare_swap_transactions_from_quote(
                    quote=quote,
                    user_address=user_address,
                    suggested_params=suggested_params,
                )
                return txn_group
            else:
                raise NotImplementedError()

        elif quote_count == 2:
            pools = self.pools
            swap_type = quotes[0].swap_type
            tinyman_client = pools[0].client
            user_address = user_address or tinyman_client.user_address

            router_app_id = tinyman_client.router_app_id
            validator_app_id = tinyman_client.validator_app_id

            input_asset_id = quotes[0].amount_in.asset.id
            intermediary_asset_id = quotes[0].amount_out.asset.id
            output_asset_id = quotes[-1].amount_out.asset.id

            asset_in_amount = quotes[0].amount_in_with_slippage.amount
            asset_out_amount = quotes[-1].amount_out_with_slippage.amount

            txn_group = prepare_swap_router_transactions(
                router_app_id=router_app_id,
                validator_app_id=validator_app_id,
                input_asset_id=input_asset_id,
                intermediary_asset_id=intermediary_asset_id,
                output_asset_id=output_asset_id,
                asset_in_amount=asset_in_amount,
                asset_out_amount=asset_out_amount,
                swap_type=swap_type,
                user_address=user_address,
                suggested_params=suggested_params,
            )
            return txn_group

        else:
            raise NotImplementedError()

    @property
    def asset_ids(self) -> list[int]:
        asset_ids = [self.asset_in.id]

        for pool in self.pools:
            if isinstance(pool, TinymanV2Pool):
                asset_1_id = pool.asset_1.id
                asset_2_id = pool.asset_2.id
            elif isinstance(pool, TinymanV1Pool):
                asset_1_id = pool.asset1.id
                asset_2_id = pool.asset2.id
            else:
                raise NotImplementedError()

            if asset_ids[-1] == asset_1_id:
                asset_ids.append(asset_2_id)
            else:
                asset_ids.append(asset_1_id)

        return asset_ids

    @property
    def price(self):
        input_asset_id = self.asset_in.id

        pool_prices = []
        for pool in self.pools:
            if isinstance(pool, TinymanV2Pool):
                asset_1_id = pool.asset_1.id
                asset_2_id = pool.asset_2.id
                pool_asset_1_price = pool.asset_1_price
                pool_asset_2_price = pool.asset_2_price

            elif isinstance(pool, TinymanV1Pool):
                asset_1_id = pool.asset1.id
                asset_2_id = pool.asset2.id
                pool_asset_1_price = pool.asset1_price
                pool_asset_2_price = pool.asset2_price

            else:
                raise NotImplementedError()

            if input_asset_id == asset_1_id:
                pool_prices.append(pool_asset_1_price)
                input_asset_id = asset_2_id
            else:
                pool_prices.append(pool_asset_2_price)
                input_asset_id = asset_1_id

        return math.prod(pool_prices)

    def calculate_price_impact_from_quotes(self, quotes):
        swap_price = math.prod([quote.price for quote in quotes])
        route_price = self.price
        price_impact = round(1 - (swap_price / route_price), 5)
        return price_impact


def get_best_fixed_input_route(routes: list[Route], amount_in: int) -> Optional[Route]:
    best_route = None
    best_route_price_impact = None
    best_route_amount_out = None

    for route in routes:
        try:
            quotes = route.get_fixed_input_quotes(amount_in=amount_in)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        last_quote = quotes[-1]
        price_impact = route.calculate_price_impact_from_quotes(quotes)

        if (not best_route) or (
            (best_route_amount_out, -best_route_price_impact)
            < (last_quote.amount_out, -price_impact)
        ):
            best_route = route
            best_route_amount_out = last_quote.amount_out
            best_route_price_impact = price_impact

    return best_route


def get_best_fixed_output_route(routes: list[Route], amount_out: int):
    best_route = None
    best_route_price_impact = None
    best_route_amount_in = None

    for route in routes:
        try:
            quotes = route.get_fixed_output_quotes(amount_out=amount_out)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        first_quote = quotes[0]
        price_impact = route.calculate_price_impact_from_quotes(quotes)

        if (not best_route) or (
            (best_route_amount_in, best_route_price_impact)
            > (first_quote.amount_in, price_impact)
        ):
            best_route = route
            best_route_amount_in = first_quote.amount_in
            best_route_price_impact = price_impact

    return best_route

import math
from dataclasses import dataclass
from typing import Optional
from typing import Union

from algosdk.constants import MIN_TXN_FEE

from tinyman.assets import Asset, AssetAmount
from tinyman.compat import SuggestedParams
from tinyman.exceptions import PoolHasNoLiquidity, InsufficientReserves
from tinyman.utils import TransactionGroup
from tinyman.v1.pools import Pool as TinymanV1Pool
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

        assert quotes[-1].amount_out.asset.id == self.asset_out.id
        return quotes

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
        assert quotes[0].amount_in.asset.id == self.asset_in.id
        return quotes

    def prepare_swap_router_transactions_from_quotes(
        self,
        quotes: list[TinymanV2SwapQuote],
        user_address: Optional[str] = None,
        suggested_params: Optional[SuggestedParams] = None,
    ) -> TransactionGroup:
        from tinyman.swap_router.swap_router import prepare_swap_router_transactions

        quote_count = len(quotes)
        if quote_count == 2:
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
                app_call_note=tinyman_client.generate_app_call_note(),
            )
            return txn_group

        elif quote_count == 1:
            raise NotImplementedError(
                "Use prepare_swap_transactions function of the pool directly."
            )
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

    @classmethod
    def get_swap_price_from_quotes(
        cls, quotes, asset_in_algo_price: Optional[int] = None
    ):
        amount_in = quotes[0].amount_in.amount
        amount_out = quotes[-1].amount_out.amount

        if asset_in_algo_price and asset_in_algo_price > 0:
            transaction_count = cls.get_transaction_count(quotes)

            txn_fee_in_algo = MIN_TXN_FEE * transaction_count
            txn_fee_in_asset_in = txn_fee_in_algo / asset_in_algo_price
            amount_in += txn_fee_in_asset_in

        swap_price = amount_out / amount_in
        return swap_price

    def get_price_impact_from_quotes(self, quotes):
        swap_price = self.get_swap_price_from_quotes(quotes)
        route_price = self.price
        price_impact = round(1 - (swap_price / route_price), 5)
        return price_impact

    @classmethod
    def get_transaction_count(cls, quotes) -> int:
        if len(quotes) == 2:
            transaction_count = 10
        elif len(quotes) == 1:
            if quotes[0].swap_type == "fixed-input":
                transaction_count = 3
            elif quotes[0].swap_type == "fixed-output":
                transaction_count = 4
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()

        return transaction_count


def get_best_fixed_input_route(
    routes: list[Route], amount_in: int, asset_in_algo_price: Optional[float] = None
) -> Optional[Route]:
    best_route = None
    best_route_price_impact = None
    best_route_swap_price = None

    for route in routes:
        try:
            quotes = route.get_fixed_input_quotes(amount_in=amount_in)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        swap_price = route.get_swap_price_from_quotes(quotes, asset_in_algo_price)
        price_impact = route.get_price_impact_from_quotes(quotes)

        if (not best_route) or (
            (best_route_swap_price, -best_route_price_impact)
            < (swap_price, -price_impact)
        ):
            best_route = route
            best_route_swap_price = swap_price
            best_route_price_impact = price_impact

    return best_route


def get_best_fixed_output_route(
    routes: list[Route], amount_out: int, asset_in_algo_price: Optional[float] = None
):
    best_route = None
    best_route_price_impact = None
    best_route_swap_price = None

    for route in routes:
        try:
            quotes = route.get_fixed_output_quotes(amount_out=amount_out)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        swap_price = route.get_swap_price_from_quotes(quotes, asset_in_algo_price)
        price_impact = route.get_price_impact_from_quotes(quotes)

        if (not best_route) or (
            (best_route_swap_price, -best_route_price_impact)
            < (swap_price, -price_impact)
        ):
            best_route = route
            best_route_swap_price = swap_price
            best_route_price_impact = price_impact

    return best_route

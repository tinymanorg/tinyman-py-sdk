from tinyman.swap_router.routes import Route
from tinyman.exceptions import InsufficientReserves, PoolHasNoLiquidity


def get_best_fixed_input_route(routes: list[Route], amount_in: int):
    best_route = None
    best_route_max_price_impact = None
    best_route_amount_out = None

    for route in routes:
        try:
            quotes = route.get_fixed_input_quotes(amount_in=amount_in)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        last_quote = quotes[-1]
        max_price_impact = max(quote.price_impact for quote in quotes)

        if (not best_route) or (
            (best_route_amount_out, -best_route_max_price_impact)
            < (last_quote.amount_out, -max_price_impact)
        ):
            best_route = route
            best_route_amount_out = last_quote.amount_out
            best_route_max_price_impact = max_price_impact

    return best_route


def get_best_fixed_output_route(routes: list[Route], amount_out: int):
    best_route = None
    best_route_max_price_impact = None
    best_route_amount_in = None

    for route in routes:
        try:
            quotes = route.get_fixed_output_quotes(amount_out=amount_out)
        except (InsufficientReserves, PoolHasNoLiquidity):
            continue

        first_quote = quotes[0]
        max_price_impact = max(quote.price_impact for quote in quotes)

        if (not best_route) or (
            (best_route_amount_in, best_route_max_price_impact)
            > (first_quote.amount_in, max_price_impact)
        ):
            best_route = route
            best_route_amount_in = first_quote.amount_in
            best_route_max_price_impact = max_price_impact

    return best_route

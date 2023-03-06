class PoolIsNotBootstrapped(Exception):
    pass


class PoolAlreadyBootstrapped(Exception):
    pass


class PoolHasNoLiquidity(Exception):
    pass


class PoolAlreadyInitialized(Exception):
    pass


class InsufficientReserves(Exception):
    pass


class LowSwapAmountError(Exception):
    pass

class PoolIsNotBootstrapped(Exception):
    pass


class PoolAlreadyBootstrapped(Exception):
    pass


class PoolHasNoLiquidity(Exception):
    pass


class PoolAlreadyInitialized(Exception):
    pass


class InsufficientReserve(Exception):
    pass

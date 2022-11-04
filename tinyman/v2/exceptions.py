class BootstrapIsRequired(Exception):
    pass


class AlreadyBootstrapped(Exception):
    pass


class InsufficientReserve(Exception):
    pass


class PoolHasNoLiquidity(Exception):
    pass


class PoolAlreadyHasLiquidity(Exception):
    pass

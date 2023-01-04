class AlgodError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class LogicError(AlgodError):
    def __init__(self, message, txn_id=None, pc=None, app_id=None) -> None:
        super().__init__(message)
        self.txn_id = txn_id
        self.pc = pc
        self.app_id = app_id


class OverspendError(AlgodError):
    def __init__(self, txn_id, address, amount) -> None:
        super().__init__(f"Overspend by {address}. Tried to spend {amount}")
        self.txn_id = txn_id
        self.address = address
        self.amount = amount

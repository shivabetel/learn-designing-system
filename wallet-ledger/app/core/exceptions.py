import traceback


class WalletError(Exception):
    def __init__(self, message: str, status_code: int = 400, stack_trace: bool = False):
        self.message = message
        self.status_code = status_code
        self.stack_trace = traceback.format_exc() if stack_trace else None
        super().__init__(self.message)


class InsufficientBalanceError(WalletError):
    def __init__(self):
        super().__init__("Insufficient balance", status_code=422)


class WalletNotFoundError(WalletError):
    def __init__(self):
        super().__init__("Wallet Account not found", status_code=404)


class WalletFrozenError(WalletError):
    def __init__(self):
        super().__init__("Account is frozen", status_code=403)


class DuplicateTransactionError(WalletError):
    def __init__(self):
        super().__init__("Duplicate transaction", status_code=200)


class IdempotencyConflictError(WalletError):
    def __init__(self):
        super().__init__("Idempotency key conflict", status_code=409)

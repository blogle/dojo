"""Budgeting domain specific exceptions."""


class BudgetingError(Exception):
    """Base class for budgeting domain exceptions."""


class InvalidTransaction(BudgetingError):
    """Raised when transaction input fails validation."""


class UnknownAccount(BudgetingError):
    """Raised when the referenced account does not exist or is inactive."""


class UnknownCategory(BudgetingError):
    """Raised when the referenced category does not exist or is inactive."""

"""Budgeting domain specific exceptions."""


class BudgetingError(Exception):
    """Base class for budgeting domain exceptions."""


class InvalidTransaction(BudgetingError):
    """Raised when transaction input fails validation."""


class UnknownAccount(BudgetingError):
    """Raised when the referenced account does not exist or is inactive."""


class UnknownCategory(BudgetingError):
    """Raised when the referenced category does not exist or is inactive."""


class AccountAlreadyExists(BudgetingError):
    """Raised when attempting to create an account with a duplicate identifier."""


class AccountNotFound(BudgetingError):
    """Raised when the requested account cannot be located."""


class CategoryAlreadyExists(BudgetingError):
    """Raised when attempting to create a category with a duplicate identifier."""


class CategoryNotFound(BudgetingError):
    """Raised when the requested budget category cannot be located."""

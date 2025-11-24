"""Budgeting domain specific exceptions."""


class BudgetingError(Exception):
    """
    Base class for budgeting domain exceptions.

    All custom exceptions within the budgeting domain inherit from this class,
    providing a common base for error handling.
    """


class InvalidTransaction(BudgetingError):
    """
    Raised when transaction input fails validation.

    Notes
    -----
    This exception is typically raised when an attempt to create or update a transaction
    includes data that does not meet the defined business rules or schema constraints.
    """


class UnknownAccount(BudgetingError):
    """
    Raised when the referenced account does not exist or is inactive.

    Notes
    -----
    This exception indicates that an operation was attempted on an account
    that either does not exist in the system or has been deactivated.
    """


class UnknownCategory(BudgetingError):
    """
    Raised when the referenced category does not exist or is inactive.

    Notes
    -----
    This exception signifies an attempt to use a budgeting category that
    cannot be found or is not currently active.
    """


class AccountAlreadyExists(BudgetingError):
    """
    Raised when attempting to create an account with a duplicate identifier.

    Notes
    -----
    This exception is triggered when a new account creation request
    specifies an `account_id` that is already in use by an existing account.
    """


class AccountNotFound(BudgetingError):
    """
    Raised when the requested account cannot be located.

    Notes
    -----
    This exception is raised when an attempt to retrieve or modify an account
    by its ID fails to find a matching active account.
    """


class CategoryAlreadyExists(BudgetingError):
    """
    Raised when attempting to create a category with a duplicate identifier.

    Notes
    -----
    This exception occurs when a new category creation request uses
    a `category_id` that is already assigned to an existing category.
    """


class CategoryNotFound(BudgetingError):
    """
    Raised when the requested budget category cannot be located.

    Notes
    -----
    This exception is raised when an operation requires a specific budgeting category
    but cannot find an active category matching the provided identifier.
    """


class GroupAlreadyExists(BudgetingError):
    """
    Raised when attempting to create a category group with a duplicate identifier.

    Notes
    -----
    This exception is thrown when a new category group creation request
    attempts to use a `group_id` that is already in use.
    """


class GroupNotFound(BudgetingError):
    """
    Raised when the requested category group cannot be located.

    Notes
    -----
    This exception occurs when an operation targets a category group
    that does not exist in the system.
    """

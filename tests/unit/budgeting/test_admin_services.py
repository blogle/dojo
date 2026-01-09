"""
Unit tests for account and budget category admin services.

This module contains unit tests that verify the correct behavior of the
`AccountAdminService` and `BudgetCategoryAdminService`, focusing on
CRUD operations for accounts, categories, and category groups.
"""

from dataclasses import dataclass
from datetime import date

import duckdb
import pytest

from dojo.budgeting.errors import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    BudgetingError,
    CategoryNotFoundError,
)
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    AccountUpdateRequest,
    BudgetCategoryCreateRequest,
    BudgetCategoryUpdateRequest,
)
from dojo.budgeting.services import AccountAdminService, BudgetCategoryAdminService


@dataclass(frozen=True)
class CategoryRowView:
    """
    A dataclass to represent a simplified view of a category row for testing.

    Attributes
    ----------
    name : str
        The name of the category.
    group_id : str
        The ID of the category group the category belongs to.
    """

    name: str
    group_id: str


@dataclass(frozen=True)
class CategoryGroupRowView:
    """
    A dataclass to represent a simplified view of a category group row for testing.

    Attributes
    ----------
    name : str
        The name of the category group.
    sort_order : int
        The sort order of the category group.
    """

    name: str
    sort_order: int


def test_create_account_inserts_row(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that creating an account successfully inserts a new row
    into the accounts table and returns the correct details.
    """
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="test_cash",
        name="Test Cash",
        account_type="asset",
        current_balance_minor=0,
        currency="usd",
        opened_on=date(2024, 1, 1),
    )

    created = service.create_account(in_memory_db, payload)

    # Assert that the created account's properties match the payload and expected transformations.
    assert created.account_id == "test_cash"
    assert created.currency == "USD"
    assert created.current_balance_minor == 0
    assert created.opened_on == date(2024, 1, 1)


def test_create_account_rejects_non_zero_balance(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="test_cash",
        name="Test Cash",
        account_type="asset",
        current_balance_minor=1,
        currency="USD",
    )

    with pytest.raises(BudgetingError):
        service.create_account(in_memory_db, payload)


def test_credit_account_auto_creates_payment_category(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that creating a credit liability account automatically
    creates a corresponding payment category and category group.
    """
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="visa_signature",
        name="Visa Signature",
        account_type="liability",
        account_class="credit",
        current_balance_minor=0,
        currency="usd",
    )

    # Create the credit account. This action should trigger the payment category creation.
    service.create_account(in_memory_db, payload)

    # Fetch the newly created payment category directly from the database.
    raw_category_row = in_memory_db.execute(
        "SELECT name, group_id FROM budget_categories WHERE category_id = 'payment_visa_signature'"
    ).fetchone()
    assert raw_category_row is not None
    category_row = CategoryRowView(*raw_category_row)
    # Assert its name and group_id are as expected.
    assert category_row.name == "Visa Signature"
    assert category_row.group_id == "credit_card_payments"

    # Fetch the credit card payment group directly from the database.
    raw_group_row = in_memory_db.execute(
        "SELECT name, sort_order FROM budget_category_groups WHERE group_id = 'credit_card_payments'"
    ).fetchone()
    assert raw_group_row is not None
    group_row = CategoryGroupRowView(*raw_group_row)
    # Assert its name and sort_order are as expected.
    assert group_row.name == "Credit Card Payments"
    assert group_row.sort_order == -1000


def test_duplicate_account_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that creating an account with an existing ID raises an `AccountAlreadyExistsError` error.
    """
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="dup_account",
        name="Dup",
        account_type="asset",
        current_balance_minor=0,
    )
    # Create the account once.
    service.create_account(in_memory_db, payload)

    # Attempting to create it again with the same ID should raise an error.
    with pytest.raises(AccountAlreadyExistsError):
        service.create_account(in_memory_db, payload)


def test_update_and_deactivate_account(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the update and deactivate functionalities for accounts.

    This test checks if an account's details can be successfully updated
    and subsequently deactivated, and that attempting to update a missing
    account raises an `AccountNotFoundError` error.
    """
    service = AccountAdminService()
    create_payload = AccountCreateRequest(
        account_id="needs_update",
        name="Needs Update",
        account_type="asset",
        current_balance_minor=0,
    )
    # Create an initial account to be updated and deactivated.
    service.create_account(in_memory_db, create_payload)

    # Define update payload.
    update_payload = AccountUpdateRequest(
        name="Updated",
        account_type="liability",
        current_balance_minor=0,
        currency="usd",
        opened_on=None,
        is_active=True,
    )
    # Update the account.
    updated = service.update_account(in_memory_db, "needs_update", update_payload)
    # Assert that the account's properties have been updated correctly.
    assert updated.account_type == "liability"
    assert updated.current_balance_minor == 0

    with pytest.raises(BudgetingError):
        service.update_account(
            in_memory_db,
            "needs_update",
            AccountUpdateRequest(
                name="Bad Balance",
                account_type="liability",
                current_balance_minor=1,
                currency="USD",
                opened_on=None,
                is_active=True,
            ),
        )

    # Deactivate the account.
    service.deactivate_account(in_memory_db, "needs_update")
    # Retrieve the list of accounts and check if the account's active status is False.
    refreshed = service.list_accounts(in_memory_db)
    assert any(acc.account_id == "needs_update" and acc.is_active is False for acc in refreshed)

    # Attempting to update a non-existent account should raise an error.
    with pytest.raises(AccountNotFoundError):
        service.update_account(in_memory_db, "missing", update_payload)


def test_category_crud(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the CRUD (Create, Read, Update, Deactivate) operations for budgeting categories.

    This test covers creating a new category, updating its details,
    deactivating it, and ensures that operations on a non-existent
    category raise appropriate errors.
    """
    service = BudgetCategoryAdminService()
    create_payload = BudgetCategoryCreateRequest(
        category_id="fun_money",
        name="Fun Money",
    )
    # Create a new category.
    created = service.create_category(in_memory_db, create_payload)
    # Assert that the created category's properties are correct.
    assert created.category_id == "fun_money"
    assert created.is_active is True

    # Define update payload.
    update_payload = BudgetCategoryUpdateRequest(name="Fun Stuff", is_active=False)
    # Update the category.
    updated = service.update_category(in_memory_db, "fun_money", update_payload)
    # Assert that the category's properties have been updated correctly.
    assert updated.name == "Fun Stuff"
    assert updated.is_active is False

    # Deactivate the category.
    service.deactivate_category(in_memory_db, "fun_money")
    # Retrieve the list of categories and check if the category's active status is False.
    refreshed = service.list_categories(in_memory_db)
    assert any(cat.category_id == "fun_money" and cat.is_active is False for cat in refreshed)

    # Attempting to update a non-existent category should raise an error.
    with pytest.raises(CategoryNotFoundError):
        service.update_category(in_memory_db, "missing", update_payload)

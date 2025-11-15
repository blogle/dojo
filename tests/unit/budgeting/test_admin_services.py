"""Unit tests for account and budget category admin services."""

from datetime import date

import duckdb
import pytest

from dojo.budgeting.errors import AccountAlreadyExists, AccountNotFound, CategoryNotFound
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    AccountUpdateRequest,
    BudgetCategoryCreateRequest,
    BudgetCategoryUpdateRequest,
)
from dojo.budgeting.services import AccountAdminService, BudgetCategoryAdminService


def test_create_account_inserts_row(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="test_cash",
        name="Test Cash",
        account_type="asset",
        current_balance_minor=12345,
        currency="usd",
        opened_on=date(2024, 1, 1),
    )

    created = service.create_account(in_memory_db, payload)

    assert created.account_id == "test_cash"
    assert created.currency == "USD"
    assert created.current_balance_minor == 12345
    assert created.opened_on == date(2024, 1, 1)


def test_duplicate_account_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = AccountAdminService()
    payload = AccountCreateRequest(
        account_id="dup_account",
        name="Dup",
        account_type="asset",
        current_balance_minor=0,
    )
    service.create_account(in_memory_db, payload)

    with pytest.raises(AccountAlreadyExists):
        service.create_account(in_memory_db, payload)


def test_update_and_deactivate_account(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = AccountAdminService()
    create_payload = AccountCreateRequest(
        account_id="needs_update",
        name="Needs Update",
        account_type="asset",
        current_balance_minor=500,
    )
    service.create_account(in_memory_db, create_payload)

    update_payload = AccountUpdateRequest(
        name="Updated",
        account_type="liability",
        current_balance_minor=-750,
        currency="usd",
        opened_on=None,
        is_active=True,
    )
    updated = service.update_account(in_memory_db, "needs_update", update_payload)
    assert updated.account_type == "liability"
    assert updated.current_balance_minor == -750

    service.deactivate_account(in_memory_db, "needs_update")
    refreshed = service.list_accounts(in_memory_db)
    assert any(acc.account_id == "needs_update" and acc.is_active is False for acc in refreshed)

    with pytest.raises(AccountNotFound):
        service.update_account(in_memory_db, "missing", update_payload)


def test_category_crud(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = BudgetCategoryAdminService()
    create_payload = BudgetCategoryCreateRequest(
        category_id="fun_money",
        name="Fun Money",
    )
    created = service.create_category(in_memory_db, create_payload)
    assert created.category_id == "fun_money"
    assert created.is_active is True

    update_payload = BudgetCategoryUpdateRequest(name="Fun Stuff", is_active=False)
    updated = service.update_category(in_memory_db, "fun_money", update_payload)
    assert updated.name == "Fun Stuff"
    assert updated.is_active is False

    service.deactivate_category(in_memory_db, "fun_money")
    refreshed = service.list_categories(in_memory_db)
    assert any(cat.category_id == "fun_money" and cat.is_active is False for cat in refreshed)

    with pytest.raises(CategoryNotFound):
        service.update_category(in_memory_db, "missing", update_payload)

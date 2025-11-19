"""Unit tests for budget category groups."""

import duckdb
import pytest

from dojo.budgeting.errors import GroupAlreadyExists, GroupNotFound
from dojo.budgeting.schemas import (
    BudgetCategoryCreateRequest,
    BudgetCategoryGroupCreateRequest,
    BudgetCategoryGroupUpdateRequest,
    BudgetCategoryUpdateRequest,
)
from dojo.budgeting.services import BudgetCategoryAdminService


def test_group_crud(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = BudgetCategoryAdminService()
    create_payload = BudgetCategoryGroupCreateRequest(
        group_id="monthly_bills",
        name="Monthly Bills",
        sort_order=10,
    )
    created = service.create_group(in_memory_db, create_payload)
    assert created.group_id == "monthly_bills"
    assert created.name == "Monthly Bills"
    assert created.sort_order == 10
    assert created.is_active is True

    update_payload = BudgetCategoryGroupUpdateRequest(
        name="Bills",
        sort_order=20,
        is_active=True,
    )
    updated = service.update_group(in_memory_db, "monthly_bills", update_payload)
    assert updated.name == "Bills"
    assert updated.sort_order == 20

    service.deactivate_group(in_memory_db, "monthly_bills")
    refreshed = service.list_groups(in_memory_db)
    # list_groups only returns active groups
    assert not any(g.group_id == "monthly_bills" for g in refreshed)

    with pytest.raises(GroupNotFound):
        service.update_group(in_memory_db, "missing", update_payload)


def test_duplicate_group_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = BudgetCategoryAdminService()
    payload = BudgetCategoryGroupCreateRequest(
        group_id="dup_group",
        name="Dup",
    )
    service.create_group(in_memory_db, payload)

    with pytest.raises(GroupAlreadyExists):
        service.create_group(in_memory_db, payload)


def test_category_in_group(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = BudgetCategoryAdminService()
    
    # Create group
    group_payload = BudgetCategoryGroupCreateRequest(
        group_id="savings",
        name="Savings",
    )
    service.create_group(in_memory_db, group_payload)

    # Create category in group
    cat_payload = BudgetCategoryCreateRequest(
        category_id="emergency_fund",
        name="Emergency Fund",
        group_id="savings",
    )
    created_cat = service.create_category(in_memory_db, cat_payload)
    assert created_cat.group_id == "savings"

    # Update category to move to another group (or no group)
    update_payload = BudgetCategoryUpdateRequest(
        name="Emergency Fund",
        group_id=None,
        is_active=True,
    )
    updated_cat = service.update_category(in_memory_db, "emergency_fund", update_payload)
    assert updated_cat.group_id is None

    # Move back to group
    update_payload.group_id = "savings"
    updated_cat_2 = service.update_category(in_memory_db, "emergency_fund", update_payload)
    assert updated_cat_2.group_id == "savings"

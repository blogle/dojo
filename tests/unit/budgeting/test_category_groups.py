"""
Unit tests for budget category groups.

This module contains unit tests that verify the correct behavior of the
`BudgetCategoryAdminService` with respect to creating, updating,
deactivating, and managing relationships for budget category groups.
"""

import duckdb
import pytest

from dojo.budgeting.errors import GroupAlreadyExistsError, GroupNotFoundError
from dojo.budgeting.schemas import (
    BudgetCategoryCreateRequest,
    BudgetCategoryGroupCreateRequest,
    BudgetCategoryGroupUpdateRequest,
    BudgetCategoryUpdateRequest,
)
from dojo.budgeting.services import BudgetCategoryAdminService


def test_group_crud(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the CRUD (Create, Read, Update, Deactivate) operations for budgeting category groups.

    This test covers creating a new group, updating its details,
    deactivating it, and ensures that operations on a non-existent
    group raise an `GroupNotFoundError` error.
    """
    service = BudgetCategoryAdminService()
    create_payload = BudgetCategoryGroupCreateRequest(
        group_id="monthly_bills",
        name="Monthly Bills",
        sort_order=10,
    )
    # Create a new category group.
    created = service.create_group(in_memory_db, create_payload)
    # Assert that the created group's properties are correct.
    assert created.group_id == "monthly_bills"
    assert created.name == "Monthly Bills"
    assert created.sort_order == 10
    assert created.is_active is True

    # Define update payload.
    update_payload = BudgetCategoryGroupUpdateRequest(
        name="Bills",
        sort_order=20,
        is_active=True,
    )
    # Update the category group.
    updated = service.update_group(in_memory_db, "monthly_bills", update_payload)
    # Assert that the group's properties have been updated correctly.
    assert updated.name == "Bills"
    assert updated.sort_order == 20

    # Deactivate the category group.
    service.deactivate_group(in_memory_db, "monthly_bills")
    # Retrieve the list of active groups and ensure the deactivated group is no longer present.
    refreshed = service.list_groups(in_memory_db)
    # list_groups only returns active groups, so the deactivated one should not be found.
    assert not any(g.group_id == "monthly_bills" for g in refreshed)

    # Attempting to update a non-existent group should raise an error.
    with pytest.raises(GroupNotFoundError):
        service.update_group(in_memory_db, "missing", update_payload)


def test_duplicate_group_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that creating a category group with an existing ID raises an `GroupAlreadyExistsError` error.
    """
    service = BudgetCategoryAdminService()
    payload = BudgetCategoryGroupCreateRequest(
        group_id="dup_group",
        name="Dup",
    )
    # Create the group once.
    service.create_group(in_memory_db, payload)

    # Attempting to create it again with the same ID should raise an error.
    with pytest.raises(GroupAlreadyExistsError):
        service.create_group(in_memory_db, payload)


def test_category_in_group(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the ability to assign categories to groups and move them between groups.
    """
    service = BudgetCategoryAdminService()

    # Create a category group.
    group_payload = BudgetCategoryGroupCreateRequest(
        group_id="savings",
        name="Savings",
    )
    service.create_group(in_memory_db, group_payload)

    # Create a category and assign it to the newly created group.
    cat_payload = BudgetCategoryCreateRequest(
        category_id="emergency_fund",
        name="Emergency Fund",
        group_id="savings",
    )
    created_cat = service.create_category(in_memory_db, cat_payload)
    # Assert the category is correctly assigned to the group.
    assert created_cat.group_id == "savings"

    # Update the category to move it to no group (group_id=None).
    update_payload = BudgetCategoryUpdateRequest(
        name="Emergency Fund",
        group_id=None,
        is_active=True,
    )
    updated_cat = service.update_category(in_memory_db, "emergency_fund", update_payload)
    # Assert the category is no longer in a group.
    assert updated_cat.group_id is None

    # Update the category again to move it back to the original group.
    update_payload.group_id = "savings"
    updated_cat_2 = service.update_category(in_memory_db, "emergency_fund", update_payload)
    # Assert the category is correctly reassigned to the group.
    assert updated_cat_2.group_id == "savings"

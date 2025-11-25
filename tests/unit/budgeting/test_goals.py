"""
Unit tests for budget category goal-related functionalities.

This module verifies that budgeting category goals, including their type,
amount, target date, and frequency, are correctly created, updated,
and retrieved through the `BudgetCategoryAdminService`.
"""

from datetime import date

import duckdb

from dojo.budgeting.schemas import (
    BudgetCategoryCreateRequest,
    BudgetCategoryUpdateRequest,
)
from dojo.budgeting.services import BudgetCategoryAdminService


def test_category_goals(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the creation and update of budgeting category goals.

    This test covers creating a category with a target date goal,
    then updating it to a recurring goal, asserting that the goal
    metadata is correctly persisted and retrieved at each step.
    """
    service = BudgetCategoryAdminService()

    # 1. Create category with a target date goal.
    create_payload = BudgetCategoryCreateRequest(
        category_id="vacation",
        name="Vacation",
        goal_type="target_date",
        goal_amount_minor=100000,
        goal_target_date=date(2025, 12, 31),
    )
    created = service.create_category(in_memory_db, create_payload)
    # Assert that the created category has the correct goal type, amount, and target date.
    assert created.goal_type == "target_date"
    assert created.goal_amount_minor == 100000
    assert created.goal_target_date == date(2025, 12, 31)
    assert created.goal_frequency is None

    # 2. Update the category to a recurring goal.
    update_payload = BudgetCategoryUpdateRequest(
        name="Vacation Fund",  # Name can also be updated.
        goal_type="recurring",
        goal_amount_minor=5000,
        goal_frequency="monthly",
        goal_target_date=date(2024, 1, 1),  # Next due date for a recurring goal.
        is_active=True,
    )
    updated = service.update_category(in_memory_db, "vacation", update_payload)
    # Assert that the updated category reflects the new recurring goal settings.
    assert updated.goal_type == "recurring"
    assert updated.goal_amount_minor == 5000
    assert updated.goal_frequency == "monthly"
    assert updated.goal_target_date == date(2024, 1, 1)

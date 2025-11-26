"""
Unit tests for budget category monthly state and invariants.

This module contains unit tests to verify the correct aggregation and
persistence of budget category monthly state, including allocated funds,
activity, available balances, and goal metadata.
"""

from datetime import date, timedelta

import duckdb

from dojo.budgeting.schemas import (
    BudgetCategoryCreateRequest,
    NewTransactionRequest,
)
from dojo.budgeting.services import (
    BudgetCategoryAdminService,
    TransactionEntryService,
)


def test_category_monthly_state_aggregates(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that the category monthly state correctly aggregates allocations and transactions.

    This test creates a category, allocates funds to it, and records a spending
    transaction. It then asserts that the `allocated_minor`, `activity_minor`,
    and `available_minor` fields in the category's monthly state are correct.
    """
    admin_service = BudgetCategoryAdminService()
    txn_service = TransactionEntryService()

    # Create a new budget category.
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(category_id="new_groceries", name="New Groceries"),
    )

    today = date.today()
    month_start = today.replace(day=1)

    # 1. Allocate funds (affects allocated_minor and available_minor).
    # First, inject income to ensure "Ready to Assign" has funds for allocation.
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=today,
            account_id="house_checking",  # Assuming this account exists from fixtures.
            category_id="income",  # System income category.
            amount_minor=100000,  # 1000.00 USD
        ),
    )

    # Allocate funds to the new groceries category.
    txn_service.allocate_envelope(
        in_memory_db,
        "new_groceries",
        5000,  # 50.00 USD
        month_start,
    )

    # 2. Spend funds (affects activity_minor and available_minor).
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=today,
            account_id="house_checking",
            category_id="new_groceries",
            amount_minor=-2000,  # -20.00 USD
        ),
    )

    # 3. Verify the category's aggregated state for the current month.
    categories = admin_service.list_categories(in_memory_db, month_start)
    groceries = next(c for c in categories if c.category_id == "new_groceries")

    # Assert expected values based on allocations and spending.
    assert groceries.allocated_minor == 5000  # 50.00 USD allocated
    # Activity is stored as a positive value for spending (outflows).
    assert groceries.activity_minor == 2000  # 20.00 USD spent
    assert groceries.available_minor == 3000  # 50.00 allocated - 20.00 spent = 30.00 available


def test_last_month_state_aggregates(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that the previous month's category state is correctly aggregated and surfaced.

    This test simulates allocations and spending in a past month and then checks
    if the `last_month_allocated_minor`, `last_month_activity_minor`, and
    `last_month_available_minor` fields are accurately reflected when viewing
    the current month's category details.
    """
    admin_service = BudgetCategoryAdminService()
    txn_service = TransactionEntryService()

    # Create a new budget category.
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(category_id="dining_out", name="Dining Out New"),
    )

    today = date.today()
    this_month = today.replace(day=1)
    # Calculate the start of the previous month.
    last_month = (this_month - timedelta(days=1)).replace(day=1)

    # Add income for the last month to ensure RTA.
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=last_month,
            account_id="house_checking",
            category_id="income",
            amount_minor=100000,
        ),
    )

    # Allocate and spend funds in the last month.
    txn_service.allocate_envelope(
        in_memory_db,
        "dining_out",
        10000,  # 100.00 USD allocated
        last_month,
    )

    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=last_month,
            account_id="house_checking",
            category_id="dining_out",
            amount_minor=-4000,  # -40.00 USD spent
        ),
    )

    # Verify this month's view of last month's data.
    categories = admin_service.list_categories(in_memory_db, this_month)
    dining = next(c for c in categories if c.category_id == "dining_out")

    # Assert that the previous month's aggregated values are correctly surfaced.
    assert dining.last_month_allocated_minor == 10000
    assert dining.last_month_activity_minor == 4000
    # Last month available = 10000 (allocated) - 4000 (activity) = 6000.
    assert dining.last_month_available_minor == 6000


def test_goal_metadata_persistence(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that goal-related metadata for a category is correctly persisted and retrieved.

    This test creates a category with specific goal settings and then asserts
    that these settings are accurately reflected when the category details are fetched.
    """
    admin_service = BudgetCategoryAdminService()

    # Create a new budget category with goal metadata.
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(
            category_id="vacation",
            name="Vacation",
            goal_type="target_date",
            goal_amount_minor=50000,
            goal_target_date=date(2025, 12, 31),
        ),
    )

    # Fetch the categories and find the one just created.
    categories = admin_service.list_categories(in_memory_db)
    vacation = next(c for c in categories if c.category_id == "vacation")

    # Assert that the goal metadata is correctly persisted.
    assert vacation.goal_type == "target_date"
    assert vacation.goal_amount_minor == 50000
    assert vacation.goal_target_date == date(2025, 12, 31)

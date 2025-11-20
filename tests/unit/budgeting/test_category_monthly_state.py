"""Unit tests for budget category monthly state and invariants."""

from datetime import date, timedelta

import duckdb
import pytest

from dojo.budgeting.schemas import (
    BudgetCategoryCreateRequest,
    NewTransactionRequest,
    BudgetAllocationRequest,
)
from dojo.budgeting.services import (
    BudgetCategoryAdminService,
    TransactionEntryService,
)


def test_category_monthly_state_aggregates(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    admin_service = BudgetCategoryAdminService()
    txn_service = TransactionEntryService()
    
    # Create category
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(category_id="new_groceries", name="New Groceries")
    )
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 1. Allocate funds (affects allocated_minor and available_minor)
    # We need to have RTA first, so let's add income
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=today,
            account_id="house_checking", # Assuming this exists in conftest or we need to create it
            category_id="income",
            amount_minor=100000,
        )
    )
    
    txn_service.allocate_envelope(
        in_memory_db,
        "new_groceries",
        5000,
        month_start
    )
    
    # 2. Spend funds (affects activity_minor and available_minor)
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=today,
            account_id="house_checking",
            category_id="new_groceries",
            amount_minor=-2000,
        )
    )
    
    # 3. Verify state
    categories = admin_service.list_categories(in_memory_db, month_start)
    groceries = next(c for c in categories if c.category_id == "new_groceries")
    
    assert groceries.allocated_minor == 5000
    # Activity is positive for spending (outflows)
    assert groceries.activity_minor == 2000
    assert groceries.available_minor == 3000 # 5000 - 2000


def test_last_month_state_aggregates(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    admin_service = BudgetCategoryAdminService()
    txn_service = TransactionEntryService()
    
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(category_id="dining_out", name="Dining Out New")
    )
    
    today = date.today()
    this_month = today.replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    
    # Add income for last month
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=last_month,
            account_id="house_checking",
            category_id="income",
            amount_minor=100000,
        )
    )
    
    # Allocate and spend in last month
    txn_service.allocate_envelope(
        in_memory_db,
        "dining_out",
        10000,
        last_month
    )
    
    txn_service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=last_month,
            account_id="house_checking",
            category_id="dining_out",
            amount_minor=-4000,
        )
    )
    
    # Verify this month's view of last month's data
    categories = admin_service.list_categories(in_memory_db, this_month)
    dining = next(c for c in categories if c.category_id == "dining_out")
    
    assert dining.last_month_allocated_minor == 10000
    # Activity is positive for spending
    assert dining.last_month_activity_minor == 4000
    # Available rolls over? 
    # Last month available = 10000 - 4000 = 6000.
    # This month allocated = 0, activity = 0.
    # So available should be 6000.
    assert dining.available_minor == 6000


def test_goal_metadata_persistence(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    admin_service = BudgetCategoryAdminService()
    
    admin_service.create_category(
        in_memory_db,
        BudgetCategoryCreateRequest(
            category_id="vacation", 
            name="Vacation",
            goal_type="target_date",
            goal_amount_minor=50000,
            goal_target_date=date(2025, 12, 31)
        )
    )
    
    categories = admin_service.list_categories(in_memory_db)
    vacation = next(c for c in categories if c.category_id == "vacation")
    
    assert vacation.goal_type == "target_date"
    assert vacation.goal_amount_minor == 50000
    assert vacation.goal_target_date == date(2025, 12, 31)

from datetime import date
import duckdb
from dojo.budgeting.schemas import BudgetCategoryCreateRequest, BudgetCategoryUpdateRequest
from dojo.budgeting.services import BudgetCategoryAdminService

def test_category_goals(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = BudgetCategoryAdminService()
    
    # Create category with target date goal
    create_payload = BudgetCategoryCreateRequest(
        category_id="vacation",
        name="Vacation",
        goal_type="target_date",
        goal_amount_minor=100000,
        goal_target_date=date(2025, 12, 31),
    )
    created = service.create_category(in_memory_db, create_payload)
    assert created.goal_type == "target_date"
    assert created.goal_amount_minor == 100000
    assert created.goal_target_date == date(2025, 12, 31)
    assert created.goal_frequency is None

    # Update to recurring goal
    update_payload = BudgetCategoryUpdateRequest(
        name="Vacation Fund",
        goal_type="recurring",
        goal_amount_minor=5000,
        goal_frequency="monthly",
        goal_target_date=date(2024, 1, 1), # Next due date
        is_active=True,
    )
    updated = service.update_category(in_memory_db, "vacation", update_payload)
    assert updated.goal_type == "recurring"
    assert updated.goal_amount_minor == 5000
    assert updated.goal_frequency == "monthly"
    assert updated.goal_target_date == date(2024, 1, 1)

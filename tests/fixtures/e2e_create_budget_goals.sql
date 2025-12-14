-- Fixture for User Story 08: Create Budget (Recurring or Target Date)
-- Seeds one on-budget cash account and minimal categories so the budget modal can save.

INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES ('goal_checking', 'Goal Checking', 'asset', 500000, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role,
        updated_at = TIMESTAMP '2025-12-15 12:00:00';

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES ('household_misc', 'Household Misc', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system,
        updated_at = TIMESTAMP '2025-12-15 12:00:00';

WITH month_start AS (
    SELECT DATE '2025-12-01' AS month_start
)

INSERT INTO budget_category_monthly_state (
    category_id, month_start, allocated_minor, inflow_minor, activity_minor, available_minor
)
SELECT
    'household_misc',
    month_start,
    0,
    0,
    0,
    0
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

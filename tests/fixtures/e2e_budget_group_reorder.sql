-- Fixture for User Story 18: Reorder budget groups via drag and drop.
-- Seeds three groups with categories assigned so the table renders grouped rows.

INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES ('ordering_cash', 'Ordering Checking', 'asset', 250000, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role,
        updated_at = NOW();

INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES
    ('housing', 'Housing', 1),
    ('groceries', 'Groceries', 2),
    ('fun_money', 'Fun Money', 3)
ON CONFLICT (group_id) DO UPDATE
    SET
        name = excluded.name,
        sort_order = excluded.sort_order,
        is_active = TRUE,
        updated_at = NOW();

INSERT INTO budget_categories (category_id, group_id, name, is_active, is_system)
VALUES
    ('rent', 'housing', 'Rent', TRUE, FALSE),
    ('groceries', 'groceries', 'Groceries', TRUE, FALSE),
    ('eating_out', 'fun_money', 'Eating Out', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        group_id = excluded.group_id,
        is_active = excluded.is_active,
        is_system = excluded.is_system,
        updated_at = NOW();

WITH month_start AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) AS month_start
)

INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
SELECT
    category_id,
    month_start,
    0,
    0,
    0,
    0
FROM month_start
CROSS JOIN (
    SELECT 'rent' AS category_id
    UNION ALL
    SELECT 'groceries'
    UNION ALL
    SELECT 'eating_out'
) AS categories
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

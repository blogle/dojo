-- Fixture for User Story 10: Group-level Quick Allocation (sufficient RTA)
-- Same Subscriptions group as the insufficient scenario, but Ready-to-Assign starts at $100.

INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES ('group_cash', 'Group Checking', 'asset', 10000, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
SET name = EXCLUDED.name,
    account_type = EXCLUDED.account_type,
    current_balance_minor = EXCLUDED.current_balance_minor,
    currency = EXCLUDED.currency,
    is_active = EXCLUDED.is_active,
    account_class = EXCLUDED.account_class,
    account_role = EXCLUDED.account_role,
    updated_at = NOW();

INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES ('subscriptions', 'Subscriptions', 10)
ON CONFLICT (group_id) DO UPDATE
SET name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE,
    updated_at = NOW();

INSERT INTO budget_categories (category_id, group_id, name, is_active, is_system)
VALUES
    ('netflix', 'subscriptions', 'Netflix', TRUE, FALSE),
    ('spotify', 'subscriptions', 'Spotify', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
SET name = EXCLUDED.name,
    group_id = EXCLUDED.group_id,
    is_active = EXCLUDED.is_active,
    is_system = EXCLUDED.is_system,
    updated_at = NOW();

WITH current_month AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) AS month_start
),
prev_month AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month' AS month_start
),
category_spend AS (
    SELECT 'netflix' AS category_id, 1500 AS spent_minor
    UNION ALL
    SELECT 'spotify', 2500
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
    cs.category_id,
    cm.month_start,
    0,
    0,
    0,
    0
FROM current_month AS cm
CROSS JOIN category_spend AS cs
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

WITH prev_month AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month' AS month_start
),
category_spend AS (
    SELECT 'netflix' AS category_id, 1500 AS spent_minor
    UNION ALL
    SELECT 'spotify', 2500
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
    cs.category_id,
    pm.month_start,
    0,
    0,
    -cs.spent_minor,
    0
FROM prev_month AS pm
CROSS JOIN category_spend AS cs
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

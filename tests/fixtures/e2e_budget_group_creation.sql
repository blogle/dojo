-- Fixture for User Story 07: Budget Group Creation and Assignment Flow
-- Seeds two uncategorized envelopes so the UI can create a group and assign them.

INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget')
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

INSERT INTO budget_categories (category_id, name, is_active, is_system, group_id)
VALUES
('netflix', 'Netflix', TRUE, FALSE, NULL),
('spotify', 'Spotify', TRUE, FALSE, NULL)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system,
        group_id = excluded.group_id,
        updated_at = NOW();

WITH month_start AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) AS month_start
),

category_seeds AS (
    SELECT 'netflix' AS category_id
    UNION ALL
    SELECT 'spotify'
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
CROSS JOIN category_seeds
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

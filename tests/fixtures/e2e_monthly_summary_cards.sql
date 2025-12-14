-- Fixture for User Story 14: Display of Monthly Summary Cards Across Pages.
-- Seeds a checking account, two envelopes, a single outflow, and their monthly state so summaries stay deterministic.

INSERT INTO accounts (
    account_id,
    name,
    account_type,
    current_balance_minor,
    currency,
    is_active,
    account_class,
    account_role
)
VALUES (
    'house_checking',
    'House Checking',
    'asset',
    300000,
    'USD',
    TRUE,
    'cash',
    'on_budget'
)
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role;

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
('groceries', 'Groceries', TRUE, FALSE),
('rent', 'Rent', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

-- Opening balance ledger entry to tie the account balance to the ledger.
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    status,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES (
    '00000000-0000-0000-0000-0000000f1401',
    '00000000-0000-0000-0000-0000000f1401',
    'house_checking',
    'opening_balance',
    DATE '2024-01-15',
    300000,
    'Opening balance import',
    'cleared',
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

-- Groceries outflow that drives the "Spent this month" summary.
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    status,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES (
    '00000000-0000-0000-0000-0000000f1402',
    '00000000-0000-0000-0000-0000000f1402',
    'house_checking',
    'groceries',
    DATE '2024-01-15',
    -15000,
    'Groceries run',
    'cleared',
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET
    current_balance_minor = 285000,
    updated_at = TIMESTAMP '2024-01-15 12:00:00'
WHERE account_id = 'house_checking';

WITH month_start AS (
    SELECT DATE '2024-01-01' AS month_start
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
    'groceries',
    month_start,
    20000,
    0,
    15000,
    35000
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

WITH month_start AS (
    SELECT DATE '2024-01-01' AS month_start
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
    'rent',
    month_start,
    25000,
    0,
    0,
    15000
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

INSERT INTO budget_allocations (
    allocation_id,
    concept_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    is_active,
    valid_from,
    recorded_at
)
VALUES
(
    '00000000-0000-0000-0000-0000000f1403',
    '00000000-0000-0000-0000-0000000f1403',
    DATE '2024-01-01',
    DATE '2024-01-01',
    NULL,
    'groceries',
    20000,
    'Initial budget',
    TRUE,
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '2024-01-15 12:00:00'
),
(
    '00000000-0000-0000-0000-0000000f1404',
    '00000000-0000-0000-0000-0000000f1404',
    DATE '2024-01-01',
    DATE '2024-01-01',
    NULL,
    'rent',
    25000,
    'Initial budget',
    TRUE,
    TIMESTAMP '2024-01-15 12:00:00',
    TIMESTAMP '2024-01-15 12:00:00'
);


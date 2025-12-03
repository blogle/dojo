-- Fixture for User Story 02: Rolling with the Punches (cover overspending).
-- Seeds Dining Out ($100) and Groceries ($500) envelopes plus a funded House Checking account.

-- Accounts
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
        account_role = excluded.account_role;

-- Categories
INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
('dining_out', 'Dining Out', TRUE, FALSE),
('groceries', 'Groceries', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

-- Opening balance transaction for House Checking so ledger drives balances.
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
    '00000000-0000-0000-0000-0000000f0201',
    '00000000-0000-0000-0000-0000000f0201',
    'house_checking',
    'opening_balance',
    CURRENT_DATE,
    100000,
    'Opening balance import',
    'cleared',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET
    current_balance_minor = 100000,
    updated_at = NOW()
WHERE account_id = 'house_checking';

-- Monthly state for Dining Out ($100) and Groceries ($500).
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
    'dining_out',
    month_start,
    10000,
    0,
    0,
    10000
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

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
    'groceries',
    month_start,
    50000,
    0,
    0,
    50000
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

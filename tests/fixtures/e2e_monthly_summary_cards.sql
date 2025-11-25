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
    name = EXCLUDED.name,
    account_type = EXCLUDED.account_type,
    current_balance_minor = EXCLUDED.current_balance_minor,
    currency = EXCLUDED.currency,
    is_active = EXCLUDED.is_active,
    account_class = EXCLUDED.account_class,
    account_role = EXCLUDED.account_role;

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
    ('groceries', 'Groceries', TRUE, FALSE),
    ('rent', 'Rent', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active,
    is_system = EXCLUDED.is_system;

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
    CURRENT_DATE,
    300000,
    'Opening balance import',
    'cleared',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
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
    CURRENT_DATE,
    -15000,
    'Groceries run',
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
    current_balance_minor = 285000,
    updated_at = NOW()
WHERE account_id = 'house_checking';

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
SELECT 'groceries', month_start, 20000, 0, 15000, 35000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET
    allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

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
SELECT 'rent', month_start, 25000, 0, 0, 15000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET
    allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

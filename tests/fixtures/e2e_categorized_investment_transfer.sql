-- Fixture for User Story 04: Categorized Investment Transfer.
-- Sets up on-budget checking + brokerage accounts plus a Future Home envelope funded with $1,000.

-- Accounts
INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES
('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget'),
('brokerage_account', 'Brokerage', 'asset', 0, 'USD', TRUE, 'investment', 'on_budget')
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
VALUES ('future_home', 'Future Home', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

-- Opening balances ensure ledger-derived account balances.
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
VALUES
(
    '00000000-0000-0000-0000-0000000f0401',
    '00000000-0000-0000-0000-0000000f0401',
    'house_checking',
    'opening_balance',
    CURRENT_DATE,
    5000000,
    'Opening balance import',
    'cleared',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
),
(
    '00000000-0000-0000-0000-0000000f0402',
    '00000000-0000-0000-0000-0000000f0402',
    'brokerage_account',
    'opening_balance',
    CURRENT_DATE,
    500000,
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
    current_balance_minor = 5000000,
    updated_at = NOW()
WHERE account_id = 'house_checking';

UPDATE accounts
SET
    current_balance_minor = 500000,
    updated_at = NOW()
WHERE account_id = 'brokerage_account';

-- Future Home monthly state with $1,000 available/budgeted.
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
    'future_home',
    month_start,
    100000,
    0,
    0,
    100000
FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

-- Fixture for User Story 12: Investment Transfers Treated as Spending.
-- Sets up on-budget checking + brokerage accounts and a Down Payment Fund envelope with $400 available.

-- Accounts
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES
    ('house_checking', 'House Checking', 'asset', 1000000, 'USD', TRUE, 'cash', 'on_budget'),
    ('brokerage_account', 'Brokerage', 'asset', 200000, 'USD', TRUE, 'investment', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET name = EXCLUDED.name,
        account_type = EXCLUDED.account_type,
        current_balance_minor = EXCLUDED.current_balance_minor,
        currency = EXCLUDED.currency,
        is_active = EXCLUDED.is_active,
        account_class = EXCLUDED.account_class,
        account_role = EXCLUDED.account_role;

-- Categories
INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES ('down_payment_fund', 'Down Payment Fund', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = EXCLUDED.is_active,
        is_system = EXCLUDED.is_system;

-- Opening balance transactions so ledger and account totals stay consistent.
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
    ('00000000-0000-0000-0000-0000000f1201', '00000000-0000-0000-0000-0000000f1201', 'house_checking', 'opening_balance', CURRENT_DATE, 1000000, 'Opening balance fixture', 'cleared', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31 00:00:00', TRUE, 'fixture'),
    ('00000000-0000-0000-0000-0000000f1202', '00000000-0000-0000-0000-0000000f1202', 'brokerage_account', 'opening_balance', CURRENT_DATE, 200000, 'Opening balance fixture', 'cleared', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31 00:00:00', TRUE, 'fixture')
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET current_balance_minor = 1000000,
    updated_at = NOW()
WHERE account_id = 'house_checking';

UPDATE accounts
SET current_balance_minor = 200000,
    updated_at = NOW()
WHERE account_id = 'brokerage_account';

-- Down Payment Fund monthly budgeting state with $400 available and zero activity.
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
SELECT 'down_payment_fund', month_start, 40000, 0, 0, 40000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

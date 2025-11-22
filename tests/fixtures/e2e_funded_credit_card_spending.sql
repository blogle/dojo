-- Fixture for User Story 03: Funded Credit Card Spending.
-- Ensures cash + credit accounts plus funding envelopes for Gas and Visa Signature Payment.

-- Accounts
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES
    ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget'),
    ('visa_signature', 'Visa Signature', 'liability', 0, 'USD', TRUE, 'credit', 'on_budget')
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
VALUES
    ('gas', 'Gas', TRUE, FALSE),
    ('payment_visa_signature', 'Visa Signature Payment', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = EXCLUDED.is_active,
        is_system = EXCLUDED.is_system;

-- Opening balance transaction seeds the checking account balance on the ledger.
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
    '00000000-0000-0000-0000-0000000f0301',
    '00000000-0000-0000-0000-0000000f0301',
    'house_checking',
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
SET current_balance_minor = 500000,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = 'house_checking';

-- Ensure monthly state reflects $100 assigned to Gas and $0 to Payment.
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
SELECT 'gas', month_start, 10000, 0, 0, 10000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
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
SELECT 'payment_visa_signature', month_start, 0, 0, 0, 0 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

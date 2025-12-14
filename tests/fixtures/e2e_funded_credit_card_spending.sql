-- Fixture for User Story 03: Funded Credit Card Spending.
-- Ensures cash + credit accounts plus funding envelopes for Gas and Visa Signature Payment.

-- Accounts
INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES
('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget'),
('visa_signature', 'Visa Signature', 'liability', 0, 'USD', TRUE, 'credit', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role;

-- Categories / Groups
INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES ('credit_card_payments', 'Credit Card Payments', -1000)
ON CONFLICT (group_id) DO UPDATE
    SET
        name = excluded.name,
        sort_order = excluded.sort_order,
        is_active = TRUE,
        updated_at = TIMESTAMP '2025-12-15 12:00:00';

INSERT INTO budget_categories (category_id, name, group_id, is_active, is_system)
VALUES
('gas', 'Gas', NULL, TRUE, FALSE),
('payment_visa_signature', 'Visa Signature', 'credit_card_payments', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        group_id = excluded.group_id,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

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
    DATE '2025-12-15',
    500000,
    'Opening balance import',
    'cleared',
    TIMESTAMP '2025-12-15 12:00:00',
    TIMESTAMP '2025-12-15 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET
    current_balance_minor = 500000,
    updated_at = TIMESTAMP '2025-12-15 12:00:00'
WHERE account_id = 'house_checking';

-- Ensure monthly state reflects $100 assigned to Gas and $0 to Payment.
WITH month_start AS (
    SELECT DATE '2025-12-01' AS month_start
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
    'gas',
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
    SELECT DATE '2025-12-01' AS month_start
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
    'payment_visa_signature',
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

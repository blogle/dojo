-- Fixture for User Story 06: Editable Ledger Rows (Correcting data entry).
-- Seeds a checking account with $5,000 and a Utilities envelope budgeted at $400.

INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
SET name = EXCLUDED.name,
    account_type = EXCLUDED.account_type,
    current_balance_minor = EXCLUDED.current_balance_minor,
    currency = EXCLUDED.currency,
    is_active = EXCLUDED.is_active,
    account_class = EXCLUDED.account_class,
    account_role = EXCLUDED.account_role;

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES ('utilities', 'Utilities', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
SET name = EXCLUDED.name,
    is_active = EXCLUDED.is_active,
    is_system = EXCLUDED.is_system;

-- Opening ledger entry establishes the $5,000 cash balance.
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
    '00000000-0000-0000-0000-0000000f0601',
    '00000000-0000-0000-0000-0000000f0601',
    'house_checking',
    'opening_balance',
    '2025-11-15',
    500000,
    'Opening balance import',
    'cleared',
    TIMESTAMP '2025-11-15 12:00:00',
    TIMESTAMP '2025-11-15 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET current_balance_minor = 500000,
    updated_at = TIMESTAMP '2025-11-15 12:00:00'
WHERE account_id = 'house_checking';

INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
VALUES ('utilities', '2025-11-01', 40000, 0, 0, 40000)
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor,
    inflow_minor = EXCLUDED.inflow_minor,
    activity_minor = EXCLUDED.activity_minor,
    available_minor = EXCLUDED.available_minor;

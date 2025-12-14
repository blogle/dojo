-- Fixture for User Story 11: Categorized Allocation Ledger Functionality.
-- Anchored to the Cypress default test month: December 2025.

-- Account: on-budget cash balance $1,100.00 (RTA $900 + envelopes $200).
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
    110000,
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

-- Categories
INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
('groceries', 'Groceries', TRUE, FALSE),
('rent', 'Rent', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

-- Ledger transactions:
-- - $600 opening balance in November (counts in cash balance, not December inflow)
-- - $500 income in December (counts as December cash inflow)
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
    '00000000-0000-0000-0000-0000000f1101',
    '00000000-0000-0000-0000-0000000f1101',
    'house_checking',
    'opening_balance',
    DATE '2025-11-30',
    60000,
    'Opening balance import',
    'cleared',
    TIMESTAMP '2025-11-30 12:00:00',
    TIMESTAMP '2025-11-30 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

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
    '00000000-0000-0000-0000-0000000f1102',
    '00000000-0000-0000-0000-0000000f1102',
    'house_checking',
    'available_to_budget',
    DATE '2025-12-05',
    50000,
    'Paycheck deposit',
    'cleared',
    TIMESTAMP '2025-12-05 12:00:00',
    TIMESTAMP '2025-12-05 12:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    'fixture'
)
ON CONFLICT (transaction_version_id) DO NOTHING;

UPDATE accounts
SET
    current_balance_minor = 110000,
    updated_at = TIMESTAMP '2025-12-15 12:00:00'
WHERE account_id = 'house_checking';

-- Monthly budgeting state for December 2025:
-- Groceries: $150.00 available, Rent: $50.00 available (total $200.00).
INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
VALUES
('groceries', DATE '2025-12-01', 15000, 0, 0, 15000),
('rent', DATE '2025-12-01', 5000, 0, 0, 5000)
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

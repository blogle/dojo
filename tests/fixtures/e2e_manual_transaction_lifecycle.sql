-- Fixture for User Story 05: Manual Transaction Lifecycle (Pending -> Cleared edits).
-- Seeds a checking account with $10,000 and a Dining Out envelope budgeted at $200.

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

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES ('dining_out', 'Dining Out', TRUE, FALSE),
       ('groceries', 'Groceries', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

-- Opening ledger entry establishes the $10,000 cash balance.
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
    '00000000-0000-0000-0000-0000000f0501',
    '00000000-0000-0000-0000-0000000f0501',
    'house_checking',
    'opening_balance',
    '2025-11-15',
    1000000,
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
SET
    current_balance_minor = 1000000,
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
VALUES ('dining_out', '2025-11-01', 20000, 0, 0, 20000)
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = excluded.allocated_minor,
        inflow_minor = excluded.inflow_minor,
        activity_minor = excluded.activity_minor,
        available_minor = excluded.available_minor;

CREATE TABLE IF NOT EXISTS seeded_for_test (id INTEGER);

DELETE FROM transactions WHERE account_id IN ('unit_reconciled_checking', 'unit_reconciled_credit');
DELETE FROM budget_category_monthly_state WHERE category_id IN ('unit_everyday_spend', 'unit_buffer');
DELETE FROM budget_categories WHERE category_id IN ('unit_everyday_spend', 'unit_buffer');
DELETE FROM accounts WHERE account_id IN ('unit_reconciled_checking', 'unit_reconciled_credit');

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
VALUES
    (
        'unit_reconciled_checking',
        'Unit Test Checking',
        'asset',
        250000,
        'USD',
        TRUE,
        'cash',
        'on_budget'
    ),
    (
        'unit_reconciled_credit',
        'Unit Test Credit Card',
        'liability',
        -125000,
        'USD',
        TRUE,
        'credit',
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
    ('unit_everyday_spend', 'Unit Everyday Spend', TRUE, FALSE),
    ('unit_buffer', 'Unit Rollover Buffer', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
SET
    name = excluded.name,
    is_active = excluded.is_active,
    is_system = excluded.is_system;

INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
VALUES
    ('unit_everyday_spend', DATE '2025-01-01', 60000, 0, -45000, 15000),
    ('unit_everyday_spend', DATE '2025-02-01', 40000, 0, -25000, 15000),
    ('unit_buffer', DATE '2025-01-01', 0, 150000, 0, 150000),
    ('unit_buffer', DATE '2025-02-01', 0, 0, 0, 150000)
ON CONFLICT (category_id, month_start) DO UPDATE
SET
    allocated_minor = excluded.allocated_minor,
    inflow_minor = excluded.inflow_minor,
    activity_minor = excluded.activity_minor,
    available_minor = excluded.available_minor;

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
        '00000000-0000-0000-0000-000000000111',
        '00000000-0000-0000-0000-000000000001',
        'unit_reconciled_checking',
        'unit_everyday_spend',
        DATE '2025-01-31',
        -45000,
        'January groceries',
        'cleared',
        TIMESTAMP '2025-01-31 22:15:00+00:00',
        TIMESTAMP '2025-01-31 22:15:00+00:00',
        TIMESTAMP '9999-12-31 00:00:00',
        TRUE,
        'fixture'
    ),
    (
        '00000000-0000-0000-0000-000000000211',
        '00000000-0000-0000-0000-000000000002',
        'unit_reconciled_checking',
        'unit_buffer',
        DATE '2025-02-01',
        150000,
        'Rollover buffer top-up',
        'cleared',
        TIMESTAMP '2025-02-01 00:05:00+00:00',
        TIMESTAMP '2025-02-01 00:05:00+00:00',
        TIMESTAMP '9999-12-31 00:00:00',
        TRUE,
        'fixture'
    ),
    (
        '00000000-0000-0000-0000-000000000311',
        '00000000-0000-0000-0000-000000000003',
        'unit_reconciled_credit',
        'unit_everyday_spend',
        DATE '2025-02-03',
        -25000,
        'Credit card groceries',
        'cleared',
        TIMESTAMP '2025-02-03 15:30:00+00:00',
        TIMESTAMP '2025-02-03 15:30:00+00:00',
        TIMESTAMP '9999-12-31 00:00:00',
        TRUE,
        'fixture'
    );

-- Fixture for testing editable allocations
-- 1. Setup Account
INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO NOTHING;

-- 2. Setup Categories
INSERT INTO budget_categories (category_id, name, is_active) VALUES ('groceries', 'Groceries', TRUE) ON CONFLICT (
    category_id
) DO NOTHING;
INSERT INTO budget_categories (category_id, name, is_active) VALUES ('utilities', 'Utilities', TRUE) ON CONFLICT (
    category_id
) DO NOTHING;

-- 3. Income to generate RTA ($1000.00)
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    status,
    recorded_at,
    is_active
) VALUES (
    uuid(),
    uuid(),
    'house_checking',
    'available_to_budget',
    DATE '2025-01-15',
    100000,
    'cleared',
    TIMESTAMP '2025-01-15 12:00:00',
    TRUE
);
UPDATE accounts SET current_balance_minor = 100000
WHERE account_id = 'house_checking';

-- 4. Initial Allocation to Groceries ($500.00)
INSERT INTO budget_allocations (
    allocation_id,
    concept_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    is_active,
    created_at
) VALUES (
    uuid(),
    uuid(),
    DATE '2025-01-15',
    DATE '2025-01-01',
    NULL,
    'groceries',
    50000,
    'Initial allocation',
    TRUE,
    TIMESTAMP '2025-01-15 12:00:00'
);

-- 5. Update monthly state for Groceries (Allocated: 50000, Available: 50000)
INSERT INTO budget_category_monthly_state (category_id, month_start, allocated_minor, available_minor, activity_minor)
VALUES ('groceries', DATE '2025-01-01', 50000, 50000, 0);

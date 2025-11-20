-- Core development/demo seed data for Dojo budgeting flows.
-- Idempotent inserts ensure repeated runs do not duplicate rows.

INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, opened_on, account_class, account_role)
VALUES
    (
        'house_checking',
        'House Checking',
        'asset',
        500000,
        'USD',
        TRUE,
        DATE '2020-01-01',
        'cash',
        'on_budget'
    ),
    (
        'house_savings',
        'House Savings',
        'asset',
        1250000,
        'USD',
        TRUE,
        DATE '2018-06-01',
        'cash',
        'on_budget'
    ),
    (
        'house_credit_card',
        'House Credit Card',
        'liability',
        250000,
        'USD',
        TRUE,
        DATE '2021-03-15',
        'credit',
        'on_budget'
    )
ON CONFLICT (account_id) DO UPDATE
    SET name = EXCLUDED.name,
        account_type = EXCLUDED.account_type,
        current_balance_minor = EXCLUDED.current_balance_minor,
        currency = EXCLUDED.currency,
        is_active = EXCLUDED.is_active,
        opened_on = COALESCE(EXCLUDED.opened_on, opened_on),
        account_class = EXCLUDED.account_class,
        account_role = EXCLUDED.account_role;

INSERT INTO budget_categories (category_id, name, is_active)
VALUES
    ('groceries', 'Groceries', TRUE),
    ('income', 'Income', TRUE),
    ('housing', 'Housing', TRUE)
ON CONFLICT (category_id) DO NOTHING;

INSERT INTO cash_account_details (detail_id, account_id, interest_rate_apy)
VALUES
    ('00000000-0000-0000-0000-000000000010', 'house_checking', 0.01),
    ('00000000-0000-0000-0000-000000000011', 'house_savings', 0.02)
ON CONFLICT (detail_id) DO NOTHING;

INSERT INTO credit_account_details (detail_id, account_id, apr, credit_limit_minor)
VALUES
    ('00000000-0000-0000-0000-000000000012', 'house_credit_card', 0.21, 500000)
ON CONFLICT (detail_id) DO NOTHING;

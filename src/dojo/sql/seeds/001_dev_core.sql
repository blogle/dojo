-- Core development/demo seed data for Dojo budgeting flows.
-- Idempotent inserts ensure repeated runs do not duplicate rows.

INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, opened_on, account_class, account_role
)
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
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        opened_on = COALESCE(excluded.opened_on, opened_on),
        account_class = excluded.account_class,
        account_role = excluded.account_role;

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

-- Canonical test fixture for house accounts and categories.
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES
    ('house_checking', 'House Checking', 'asset', 500000, 'USD', TRUE, 'cash', 'on_budget'),
    ('house_savings', 'House Savings', 'asset', 1250000, 'USD', TRUE, 'cash', 'on_budget'),
    ('house_credit_card', 'House Credit Card', 'liability', 250000, 'USD', TRUE, 'credit', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET name = EXCLUDED.name,
        account_type = EXCLUDED.account_type,
        current_balance_minor = EXCLUDED.current_balance_minor,
        currency = EXCLUDED.currency,
        is_active = EXCLUDED.is_active,
        account_class = EXCLUDED.account_class,
        account_role = EXCLUDED.account_role;

INSERT INTO budget_categories (category_id, name, is_active)
VALUES
    ('groceries', 'Groceries', TRUE),
    ('income', 'Income', TRUE),
    ('housing', 'Housing', TRUE)
ON CONFLICT (category_id) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = EXCLUDED.is_active;

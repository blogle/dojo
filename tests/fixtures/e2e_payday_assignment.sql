-- Fixture for the Payday Assignment user story e2e scenario.
-- Ensures a single on-budget checking account and three active envelopes.
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES
    ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET name = EXCLUDED.name,
        account_type = EXCLUDED.account_type,
        current_balance_minor = EXCLUDED.current_balance_minor,
        currency = EXCLUDED.currency,
        is_active = EXCLUDED.is_active,
        account_class = EXCLUDED.account_class,
        account_role = EXCLUDED.account_role;

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
    ('rent', 'Rent', TRUE, FALSE),
    ('groceries', 'Groceries', TRUE, FALSE),
    ('savings', 'Savings', TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = EXCLUDED.is_active,
        is_system = EXCLUDED.is_system;

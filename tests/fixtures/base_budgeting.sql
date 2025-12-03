-- Canonical test fixture for house accounts and categories.
INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES
('house_checking', 'House Checking', 'asset', 500000, 'USD', TRUE, 'cash', 'on_budget'),
('house_savings', 'House Savings', 'asset', 1250000, 'USD', TRUE, 'cash', 'on_budget'),
('house_credit_card', 'House Credit Card', 'liability', -250000, 'USD', TRUE, 'credit', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role;

INSERT INTO budget_categories (category_id, name, is_active)
VALUES
('groceries', 'Groceries', TRUE),
('income', 'Income', TRUE),
('housing', 'Housing', TRUE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active;

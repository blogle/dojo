INSERT INTO budget_categories (category_id, name, is_active)
VALUES
('account_transfer', 'Account Transfer (system)', FALSE),
('opening_balance', 'Opening Balance', FALSE)
ON CONFLICT (category_id) DO UPDATE SET
    name = excluded.name,
    is_active = excluded.is_active;

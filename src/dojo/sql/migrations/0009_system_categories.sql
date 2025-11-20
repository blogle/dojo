ALTER TABLE budget_categories ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;

UPDATE budget_categories
SET is_system = COALESCE(is_system, FALSE);

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
    ('account_transfer', 'Account Transfer', TRUE, TRUE),
    ('opening_balance', 'Opening Balance', TRUE, TRUE),
    ('available_to_budget', 'Available to Budget', TRUE, TRUE),
    ('balance_adjustment', 'Balance Adjustment', TRUE, TRUE)
ON CONFLICT (category_id) DO UPDATE
SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active,
    is_system = EXCLUDED.is_system,
    updated_at = NOW();

-- Fixture for User Story 15: Account Onboarding Ledger Integrity.
-- Ensures system-level categories exist so opening-balance transactions can resolve cleanly.

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
('opening_balance', 'Opening Balance', TRUE, TRUE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

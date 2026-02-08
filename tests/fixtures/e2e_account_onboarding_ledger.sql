-- Fixture for User Story 15: Account Onboarding Ledger Integrity.
-- Ensures system-level categories exist so opening-balance transactions can resolve cleanly.

-- Mark onboarding as completed so E2E stories can start on core pages.
INSERT INTO onboarding_state (onboarding_id, onboarding_mode, onboarding_status, migration_session_id)
VALUES ('primary', 'manual', 'completed', NULL)
ON CONFLICT (onboarding_id) DO UPDATE
    SET
        onboarding_mode = excluded.onboarding_mode,
        onboarding_status = excluded.onboarding_status,
        migration_session_id = excluded.migration_session_id;

INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
('opening_balance', 'Opening Balance', TRUE, TRUE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        is_active = excluded.is_active,
        is_system = excluded.is_system;

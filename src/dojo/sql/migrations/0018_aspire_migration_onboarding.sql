-- Aspire migration + onboarding state
--
-- This migration introduces:
-- - onboarding_state: first-run wizard persistence
-- - aspire_migration_sessions: resumable session metadata
-- - aspire staging tables (transactions/allocations/net worth marks)
-- - aspire legacy net worth marks storage (post-import)
-- - loan principal checkpoints (Mode A measurement commits)
-- - investment reconcile baseline support
-- - tangible valuation metadata support

-- Historical reporting must include retired entities.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS include_in_net_worth BOOLEAN DEFAULT TRUE;

UPDATE accounts
SET include_in_net_worth = COALESCE(include_in_net_worth, TRUE);

-- Investment reconcile baseline (RFC: ledger_baseline at reconcile)
ALTER TABLE investment_account_details
ADD COLUMN IF NOT EXISTS ledger_baseline_minor BIGINT DEFAULT 0;

UPDATE investment_account_details
SET ledger_baseline_minor = COALESCE(ledger_baseline_minor, 0);

-- Tangible valuations are measurement events. Store a bit of provenance.
ALTER TABLE tangible_assets ADD COLUMN IF NOT EXISTS appraisal_date DATE;
ALTER TABLE tangible_assets ADD COLUMN IF NOT EXISTS valuation_source TEXT;
ALTER TABLE tangible_assets ADD COLUMN IF NOT EXISTS note TEXT;

-- Onboarding (single-user, self-host)
CREATE TABLE IF NOT EXISTS onboarding_state (
    onboarding_id TEXT PRIMARY KEY,
    onboarding_mode TEXT,
    onboarding_status TEXT NOT NULL,
    migration_session_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (onboarding_status IN ('not_started', 'in_progress', 'completed'))
);

INSERT INTO onboarding_state (onboarding_id, onboarding_mode, onboarding_status)
SELECT 'primary', NULL, 'not_started'
WHERE NOT EXISTS (SELECT 1 FROM onboarding_state WHERE onboarding_id = 'primary');

-- Aspire migration sessions
CREATE TABLE IF NOT EXISTS aspire_migration_sessions (
    migration_session_id TEXT PRIMARY KEY,
    extraction_status TEXT NOT NULL DEFAULT 'not_started',
    mapping_status TEXT NOT NULL DEFAULT 'not_started',
    import_status TEXT NOT NULL DEFAULT 'not_started',

    spreadsheet_id TEXT,
    dataset_fingerprint TEXT,
    extracted_at TIMESTAMP,

    -- JSON blobs (stored as TEXT for DuckDB portability)
    special_labels_json TEXT,
    status_symbols_json TEXT,
    cfg_accounts_json TEXT,
    cfg_cards_json TEXT,
    hidden_accounts_json TEXT,
    hidden_categories_json TEXT,
    categories_minus_credit_cards_json TEXT,
    net_worth_assets_json TEXT,
    net_worth_debts_json TEXT,
    net_worth_categories_json TEXT,
    distinct_ntw_categories_json TEXT,

    mapping_json TEXT,
    transfer_resolutions_json TEXT,
    net_worth_decisions_json TEXT,

    import_error TEXT,
    imported_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (extraction_status IN ('not_started', 'in_progress', 'completed', 'failed')),
    CHECK (mapping_status IN ('not_started', 'in_progress', 'completed', 'failed')),
    CHECK (import_status IN ('not_started', 'in_progress', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS aspire_staging_transactions (
    migration_session_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    transaction_date DATE,
    amount_minor BIGINT NOT NULL,
    category_name TEXT,
    account_name TEXT,
    memo TEXT,
    status_raw TEXT,
    status TEXT,
    is_break BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (migration_session_id, row_index)
);

CREATE INDEX IF NOT EXISTS idx_aspire_staging_transactions_session_date
ON aspire_staging_transactions (migration_session_id, transaction_date);

CREATE TABLE IF NOT EXISTS aspire_staging_allocations (
    migration_session_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    allocation_date DATE,
    amount_minor BIGINT NOT NULL,
    from_category_name TEXT,
    to_category_name TEXT,
    PRIMARY KEY (migration_session_id, row_index)
);

CREATE INDEX IF NOT EXISTS idx_aspire_staging_allocations_session_date
ON aspire_staging_allocations (migration_session_id, allocation_date);

CREATE TABLE IF NOT EXISTS aspire_staging_net_worth_marks (
    migration_session_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    mark_date DATE,
    amount_minor BIGINT NOT NULL,
    category_name TEXT,
    note TEXT,
    breakpoint TEXT,
    PRIMARY KEY (migration_session_id, row_index)
);

CREATE INDEX IF NOT EXISTS idx_aspire_staging_marks_session_date
ON aspire_staging_net_worth_marks (migration_session_id, mark_date);

-- Persisted legacy marks stream (post-apply)
CREATE TABLE IF NOT EXISTS aspire_legacy_net_worth_marks (
    mark_id UUID PRIMARY KEY,
    migration_session_id TEXT NOT NULL,
    dataset_fingerprint TEXT NOT NULL,
    mark_date DATE NOT NULL,
    category_name TEXT NOT NULL,
    amount_minor BIGINT NOT NULL,
    note TEXT,
    breakpoint TEXT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aspire_legacy_marks_date
ON aspire_legacy_net_worth_marks (mark_date);

CREATE INDEX IF NOT EXISTS idx_aspire_legacy_marks_category
ON aspire_legacy_net_worth_marks (category_name);

-- Loan principal checkpoints (Mode A)
CREATE TABLE IF NOT EXISTS loan_principal_checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    statement_date DATE NOT NULL,
    statement_principal_minor BIGINT NOT NULL,
    delta_minor BIGINT NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
);

CREATE INDEX IF NOT EXISTS idx_loan_principal_checkpoints_account_date
ON loan_principal_checkpoints (account_id, statement_date);

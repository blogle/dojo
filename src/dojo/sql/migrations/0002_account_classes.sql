ALTER TABLE accounts
ADD COLUMN IF NOT EXISTS account_class TEXT DEFAULT 'cash';

ALTER TABLE accounts
ADD COLUMN IF NOT EXISTS account_role TEXT DEFAULT 'on_budget';

-- Seed existing rows with sensible defaults.
UPDATE accounts
SET account_class = 'cash', account_role = 'on_budget'
WHERE account_type = 'asset';

UPDATE accounts
SET account_class = 'credit', account_role = 'on_budget'
WHERE account_id = 'house_credit_card';

CREATE TABLE IF NOT EXISTS cash_account_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    interest_rate_apy DOUBLE DEFAULT 0,
    has_overdraft BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS credit_account_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    apr DOUBLE DEFAULT 0,
    credit_limit_minor BIGINT DEFAULT 0,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS accessible_asset_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    term_end_date DATE,
    is_liquid BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS investment_account_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    risk_free_sweep_rate DOUBLE DEFAULT 0,
    manager TEXT,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS loan_account_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    initial_principal_minor BIGINT DEFAULT 0,
    interest_rate_apy DOUBLE DEFAULT 0,
    term_end_date DATE,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS tangible_asset_details (
    detail_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    asset_name TEXT,
    current_fair_value_minor BIGINT NOT NULL DEFAULT 0,
    appraisal_date DATE,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Seed example SCD-2 rows for the initial accounts.
INSERT INTO cash_account_details (detail_id, account_id, interest_rate_apy)
VALUES
    ('00000000-0000-0000-0000-000000000010', 'house_checking', 0.01),
    ('00000000-0000-0000-0000-000000000011', 'house_savings', 0.02)
ON CONFLICT (detail_id) DO NOTHING;

INSERT INTO credit_account_details (detail_id, account_id, apr, credit_limit_minor)
VALUES
    ('00000000-0000-0000-0000-000000000012', 'house_credit_card', 0.21, 500000)
ON CONFLICT (detail_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('asset', 'liability')),
    current_balance_minor BIGINT NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    opened_on DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS budget_categories (
    category_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS budget_category_monthly_state (
    category_id TEXT NOT NULL,
    month_start DATE NOT NULL,
    allocated_minor BIGINT NOT NULL DEFAULT 0,
    inflow_minor BIGINT NOT NULL DEFAULT 0,
    activity_minor BIGINT NOT NULL DEFAULT 0,
    available_minor BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id, month_start),
    FOREIGN KEY (category_id) REFERENCES budget_categories (category_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_version_id UUID PRIMARY KEY,
    concept_id UUID NOT NULL,
    account_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    amount_minor BIGINT NOT NULL,
    memo TEXT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    source TEXT NOT NULL DEFAULT 'api',
    FOREIGN KEY (account_id) REFERENCES accounts (account_id),
    FOREIGN KEY (category_id) REFERENCES budget_categories (category_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_concept_active
ON transactions (concept_id, is_active);

CREATE INDEX IF NOT EXISTS idx_transactions_account_date
ON transactions (account_id, transaction_date);

CREATE TABLE IF NOT EXISTS positions (
    position_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    quantity DOUBLE NOT NULL,
    market_value_minor BIGINT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
);

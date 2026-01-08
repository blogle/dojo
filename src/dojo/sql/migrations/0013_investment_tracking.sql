-- Investment Tracking schema (Dual-State Cash Model)
--
-- NOTE: This migration intentionally drops the legacy `positions` table from 0001_core.sql
-- to resolve schema collision and replace it with the SCD2 schema defined in docs/plans/investment-tracking.md.

DROP TABLE IF EXISTS positions;

CREATE TABLE IF NOT EXISTS securities (
    security_id UUID PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT,
    type TEXT NOT NULL DEFAULT 'STOCK' CHECK (type IN ('STOCK', 'ETF', 'MUTUAL_FUND', 'CRYPTO', 'INDEX')),
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (ticker = UPPER(ticker))
);

CREATE TABLE IF NOT EXISTS market_prices (
    security_id UUID NOT NULL,
    market_date DATE NOT NULL,
    open_minor BIGINT,
    high_minor BIGINT,
    low_minor BIGINT,
    close_minor BIGINT,
    adj_close_minor BIGINT,
    volume BIGINT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (security_id, market_date),
    FOREIGN KEY (security_id) REFERENCES securities (security_id)
);

CREATE TABLE IF NOT EXISTS positions (
    position_id UUID PRIMARY KEY,
    concept_id UUID NOT NULL,
    account_id TEXT NOT NULL,
    security_id UUID NOT NULL,
    quantity DOUBLE NOT NULL,
    avg_cost_minor BIGINT NOT NULL,
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP NOT NULL DEFAULT (TIMESTAMP '9999-12-31 00:00:00'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id),
    FOREIGN KEY (security_id) REFERENCES securities (security_id)
);

CREATE INDEX IF NOT EXISTS idx_positions_concept_active
ON positions (concept_id, is_active);

CREATE INDEX IF NOT EXISTS idx_positions_account_active
ON positions (account_id, is_active);

ALTER TABLE investment_account_details
ADD COLUMN IF NOT EXISTS uninvested_cash_minor BIGINT DEFAULT 0;

UPDATE investment_account_details
SET uninvested_cash_minor = 0
WHERE uninvested_cash_minor IS NULL;

CREATE TABLE IF NOT EXISTS account_reconciliations (
    reconciliation_id UUID PRIMARY KEY,
    account_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    statement_date DATE NOT NULL,
    statement_balance_minor BIGINT NOT NULL,
    previous_reconciliation_id UUID,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id),
    FOREIGN KEY (previous_reconciliation_id) REFERENCES account_reconciliations (reconciliation_id)
);

CREATE INDEX IF NOT EXISTS idx_account_reconciliations_account_created
ON account_reconciliations (account_id, created_at);

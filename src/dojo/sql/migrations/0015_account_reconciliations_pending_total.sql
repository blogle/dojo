-- Persist pending total captured during reconciliation.
ALTER TABLE account_reconciliations
ADD COLUMN IF NOT EXISTS statement_pending_total_minor BIGINT DEFAULT 0;

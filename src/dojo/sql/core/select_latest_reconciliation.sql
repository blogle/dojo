SELECT
    reconciliation_id,
    account_id,
    created_at,
    statement_date,
    statement_balance_minor,
    statement_pending_total_minor,
    previous_reconciliation_id
FROM account_reconciliations
WHERE account_id = $account_id
ORDER BY created_at DESC
LIMIT 1;

INSERT INTO account_reconciliations (
    reconciliation_id,
    account_id,
    created_at,
    statement_date,
    statement_balance_minor,
    statement_pending_total_minor,
    previous_reconciliation_id
) VALUES (
    $reconciliation_id,
    $account_id,
    $created_at,
    $statement_date,
    $statement_balance_minor,
    $statement_pending_total_minor,
    $previous_reconciliation_id
);

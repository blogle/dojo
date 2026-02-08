SELECT
    detail_id,
    risk_free_sweep_rate,
    manager,
    is_self_directed,
    tax_classification,
    uninvested_cash_minor,
    COALESCE(ledger_baseline_minor, 0) AS ledger_baseline_minor
FROM investment_account_details
WHERE
    account_id = $account_id
    AND is_active = TRUE;

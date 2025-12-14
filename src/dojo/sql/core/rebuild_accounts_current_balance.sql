UPDATE accounts AS a
SET
    current_balance_minor = ledger.balance_minor,
    updated_at = CURRENT_TIMESTAMP
FROM (
    SELECT
        account_id,
        COALESCE(SUM(amount_minor), 0) AS balance_minor
    FROM transactions
    WHERE is_active = TRUE
    GROUP BY account_id
) AS ledger
WHERE a.account_id = ledger.account_id;

UPDATE accounts
SET current_balance_minor = current_balance_minor + ?,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = ?;
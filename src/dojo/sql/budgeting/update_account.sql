UPDATE accounts
SET
    name = ?,
    account_type = ?,
    current_balance_minor = ?,
    currency = ?,
    opened_on = ?,
    is_active = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = ?;

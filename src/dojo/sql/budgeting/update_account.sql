UPDATE accounts
SET
    name = ?,
    account_type = ?,
    account_class = ?,
    account_role = ?,
    current_balance_minor = ?,
    currency = ?,
    opened_on = ?,
    is_active = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = ?;

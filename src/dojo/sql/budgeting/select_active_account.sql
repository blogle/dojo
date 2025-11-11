SELECT
    account_id,
    name,
    account_type,
    current_balance_minor,
    currency,
    is_active
FROM accounts
WHERE account_id = ?;

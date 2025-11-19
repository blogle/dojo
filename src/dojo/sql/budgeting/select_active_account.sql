SELECT
    account_id,
    name,
    account_type,
    account_class,
    account_role,
    current_balance_minor,
    currency,
    is_active
FROM accounts
WHERE account_id = ?;

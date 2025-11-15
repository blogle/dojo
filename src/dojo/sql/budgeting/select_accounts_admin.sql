SELECT
    account_id,
    name,
    account_type,
    current_balance_minor,
    currency,
    is_active,
    opened_on,
    created_at,
    updated_at
FROM accounts
ORDER BY created_at ASC;

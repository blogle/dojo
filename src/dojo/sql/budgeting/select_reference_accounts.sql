SELECT
    account_id,
    name,
    account_type,
    account_class,
    account_role,
    current_balance_minor
FROM accounts
WHERE is_active = TRUE
ORDER BY name;
